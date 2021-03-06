import os
import abc
import tqdm
import torch
import numpy as np
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
import matplotlib.pyplot as plt

import dataloader.dataset
from dataloader.loader import Loader
from models.facebook_sparse_object_det import FBSparseObjectDet
from models.yolo_loss import yoloLoss
from models.yolo_detection import yoloDetect
from models.yolo_detection import nonMaxSuppression
from utils.statistics_pascalvoc import BoundingBoxes, BoundingBox, BBType, VOC_Evaluator, MethodAveragePrecision
import utils.visualizations as visualizations

class AbstractTrainer(abc.ABC):
    def __init__(self, settings):
        self.settings = settings

        self.model = None
        self.scheduler = None
        self.nr_classes = None
        self.val_loader = None
        self.train_loader = None
        self.nr_val_epochs = None
        self.bounding_boxes =None
        self.object_classes = None
        self.nr_train_epochs = None
        self.model_input_size = None
        self.test_loader = None
        self.nr_test_epochs = None

        if self.settings.event_representation == 'histogram':
            self.nr_input_channels = 2
        elif self.settings.event_representation == 'event_queue':
            self.nr_input_channels = 30

        self.dataset_builder = dataloader.dataset.getDataloader(self.settings.dataset_name)
        self.dataset_loader = Loader

        self.writer = SummaryWriter(self.settings.ckpt_dir)
        self.createDatasets()

        self.buildModel()
        self.optimizer = optim.Adam(filter(lambda p: p.requires_grad, self.model.parameters()),
                                    lr=self.settings.init_lr)

        if settings.steps_lr is not None:
            self.scheduler = torch.optim.lr_scheduler.MultiStepLR(self.optimizer, milestones=settings.steps_lr,
                                                                  gamma=settings.factor_lr)
        if settings.resume_training:
            self.loadCheckpoint(self.settings.resume_ckpt_file)

        self.batch_step = 0
        self.epoch_step = 0
#        self.training_loss = 0
#        self.val_batch_step = 0
#        self.validation_loss = 0
#        self.training_accuracy = 0
#        self.validation_accuracy = 0
#        self.max_validation_accuracy = 0
#        self.val_confusion_matrix = np.zeros([self.nr_classes, self.nr_classes])
        
        self.test_batch_step = 0
        self.testing_loss = 0
        self.testing_accuracy = 0
        self.test_confusion_matrix = np.zeros([self.nr_classes, self.nr_classes])

        # tqdm progress bar
        self.pbar = None

    @abc.abstractmethod
    def buildModel(self):
        """Model is constructed in child class"""
        pass

    def createDatasets(self):
        """
        Creates the validation and the training data based on the lists specified in the config/settings.yaml file.
        """
        train_dataset = self.dataset_builder(self.settings.dataset_path,
                                             self.settings.object_classes,
                                             self.settings.height,
                                             self.settings.width,
                                             self.settings.nr_events_window,
                                             augmentation=True,
                                             mode='training',
                                             event_representation=self.settings.event_representation)

        self.nr_train_epochs = int(train_dataset.nr_samples / self.settings.batch_size) + 1
        self.nr_classes = train_dataset.nr_classes
        self.object_classes = train_dataset.object_classes

        val_dataset = self.dataset_builder(self.settings.dataset_path,
                                           self.settings.object_classes,
                                           self.settings.height,
                                           self.settings.width,
                                           self.settings.nr_events_window,
                                           mode='validation',
                                           event_representation=self.settings.event_representation)
        self.nr_val_epochs = int(val_dataset.nr_samples / self.settings.batch_size) + 1
        
        test_dataset = self.dataset_builder(self.settings.dataset_path,
                                           self.settings.object_classes,
                                           self.settings.height,
                                           self.settings.width,
                                           self.settings.nr_events_window,
                                           mode='testing',
                                           event_representation=self.settings.event_representation)
        self.nr_test_epochs = int(test_dataset.nr_samples / 1) + 1
        self.nr_classes = test_dataset.nr_classes
        self.object_classes = test_dataset.object_classes

        self.train_loader = self.dataset_loader(train_dataset, batch_size=self.settings.batch_size,
                                                device=self.settings.gpu_device,
                                                num_workers=self.settings.num_cpu_workers, pin_memory=False)
        self.val_loader = self.dataset_loader(val_dataset, batch_size=self.settings.batch_size,
                                              device=self.settings.gpu_device,
                                              num_workers=self.settings.num_cpu_workers, pin_memory=False)
        self.test_loader = self.dataset_loader(test_dataset, batch_size=1,
                                              device=self.settings.gpu_device,
                                              num_workers=self.settings.num_cpu_workers, pin_memory=False)

    @staticmethod
    def denseToSparse(dense_tensor):
        """
        Converts a dense tensor to a sparse vector.

        :param dense_tensor: BatchSize x SpatialDimension_1 x SpatialDimension_2 x ... x FeatureDimension
        :return locations: NumberOfActive x (SumSpatialDimensions + 1). The + 1 includes the batch index
        :return features: NumberOfActive x FeatureDimension
        """
        non_zero_indices = torch.nonzero(torch.abs(dense_tensor).sum(axis=-1))
        locations = torch.cat((non_zero_indices[:, 1:], non_zero_indices[:, 0, None]), dim=-1)

        select_indices = non_zero_indices.split(1, dim=1)
        features = torch.squeeze(dense_tensor[select_indices], dim=-2)

        return locations, features

    def resetValidation(self):
        """Resets all the validation statistics to zero"""
        self.val_batch_step = 0
        self.validation_loss = 0
        self.validation_accuracy = 0
        self.val_confusion_matrix = np.zeros([self.nr_classes, self.nr_classes])
    
    def resetTesting(self):
        """Resets all the testing statistics to zero"""
        self.test_batch_step = 0
        self.testing_loss = 0
        self.testing_accuracy = 0
        self.test_confusion_matrix = np.zeros([self.nr_classes, self.nr_classes])

    def saveValidationStatistics(self):
        """Saves the recorded validation statistics to an event file (tensorboard)"""
        self.writer.add_scalar('Validation/Validation_Loss', self.validation_loss, self.epoch_step)
        self.writer.add_scalar('Validation/Validation_Accuracy', self.validation_accuracy, self.epoch_step)

        self.val_confusion_matrix = self.val_confusion_matrix / (np.sum(self.val_confusion_matrix, axis=-1,
                                                                        keepdims=True) + 1e-9)
        plot_confusion_matrix = visualizations.visualizeConfusionMatrix(self.val_confusion_matrix)
        self.writer.add_image('Validation/Confusion_Matrix', plot_confusion_matrix, self.epoch_step,
                              dataformats='HWC')
    
    def saveTestingStatistics(self):
        """Saves the recorded testing statistics to an event file (tensorboard)"""
        self.writer.add_scalar('Testing/Testing_Loss', self.testing_loss, self.epoch_step)
        self.writer.add_scalar('Testing/Testing_Accuracy', self.testing_accuracy, self.epoch_step)

        self.test_confusion_matrix = self.test_confusion_matrix / (np.sum(self.test_confusion_matrix, axis=-1,
                                                                        keepdims=True) + 1e-9)
        plot_confusion_matrix = visualizations.visualizeConfusionMatrix(self.test_confusion_matrix)
        self.writer.add_image('Testing/Confusion_Matrix', plot_confusion_matrix, self.epoch_step,
                              dataformats='HWC')

    def storeLossesObjectDetection(self, loss_list):
        """Writes the different losses to tensorboard"""
        loss_names = ['Overall_Loss', 'Offset_Loss', 'Shape_Loss', 'Confidence_Loss', 'Confidence_NoObject_Loss',
                      'Class_Loss']

        for i_loss in range(len(loss_list)):
            loss_value = loss_list[i_loss].data.cpu().numpy()
            self.writer.add_scalar('TrainingLoss/' + loss_names[i_loss], loss_value, self.batch_step)

    def saveBoundingBoxes(self, gt_bbox, detected_bbox):
        """
        Saves the bounding boxes in the evaluation format

        :param gt_bbox: gt_bbox[0, 0, :]: ['u', 'v', 'w', 'h', 'class_id']
        :param detected_bbox[0, :]: [batch_idx, u, v, w, h, pred_class_id, pred_class_score, object score]
        """
        image_size = self.model_input_size.cpu().numpy()
        for i_batch in range(gt_bbox.shape[0]):
            for i_gt in range(gt_bbox.shape[1]):
                gt_bbox_sample = gt_bbox[i_batch, i_gt, :]
                id_image = self.val_batch_step * self.settings.batch_size + i_batch
                if gt_bbox[i_batch, i_gt, :].sum() == 0:
                    break

                bb_gt = BoundingBox(id_image, gt_bbox_sample[-1], gt_bbox_sample[0], gt_bbox_sample[1],
                                    gt_bbox_sample[2], gt_bbox_sample[3], image_size, BBType.GroundTruth)
                self.bounding_boxes.addBoundingBox(bb_gt)

        for i_det in range(detected_bbox.shape[0]):
            det_bbox_sample = detected_bbox[i_det, :]
            id_image = self.val_batch_step * self.settings.batch_size + det_bbox_sample[0]

            bb_det = BoundingBox(id_image, det_bbox_sample[5], det_bbox_sample[1], det_bbox_sample[2],
                                 det_bbox_sample[3], det_bbox_sample[4], image_size, BBType.Detected,
                                 det_bbox_sample[6])
            self.bounding_boxes.addBoundingBox(bb_det)
    
    def saveBoundingBoxesTest(self, gt_bbox, detected_bbox):
        """
        Saves the bounding boxes in the evaluation format

        :param gt_bbox: gt_bbox[0, 0, :]: ['u', 'v', 'w', 'h', 'class_id']
        :param detected_bbox[0, :]: [batch_idx, u, v, w, h, pred_class_id, pred_class_score, object score]
        """
        image_size = self.model_input_size.cpu().numpy()
        for i_batch in range(gt_bbox.shape[0]):
            for i_gt in range(gt_bbox.shape[1]):
                gt_bbox_sample = gt_bbox[i_batch, i_gt, :]
                id_image = self.test_batch_step * self.settings.batch_size + i_batch
                if gt_bbox[i_batch, i_gt, :].sum() == 0:
                    break

                bb_gt = BoundingBox(id_image, gt_bbox_sample[-1], gt_bbox_sample[0], gt_bbox_sample[1],
                                    gt_bbox_sample[2], gt_bbox_sample[3], image_size, BBType.GroundTruth)
                self.bounding_boxes.addBoundingBox(bb_gt)

        for i_det in range(detected_bbox.shape[0]):
            det_bbox_sample = detected_bbox[i_det, :]
            id_image = self.test_batch_step * self.settings.batch_size + det_bbox_sample[0]

            bb_det = BoundingBox(id_image, det_bbox_sample[5], det_bbox_sample[1], det_bbox_sample[2],
                                 det_bbox_sample[3], det_bbox_sample[4], image_size, BBType.Detected,
                                 det_bbox_sample[6])
            self.bounding_boxes.addBoundingBox(bb_det)

    def saveValidationStatisticsObjectDetection(self):
        """Saves the statistice relevant for object detection"""
        evaluator = VOC_Evaluator()
        metrics = evaluator.GetPascalVOCMetrics(self.bounding_boxes,
                                                IOUThreshold=0.5,
                                                method=MethodAveragePrecision.EveryPointInterpolation)
        acc_AP = 0
        total_positives = 0
        for metricsPerClass in metrics:
            acc_AP += metricsPerClass['AP']
            total_positives += metricsPerClass['total positives']
        mAP = acc_AP / self.nr_classes
        self.validation_accuracy = mAP

        self.writer.add_scalar('Validation/Validation_Loss', self.validation_loss, self.epoch_step)
        self.writer.add_scalar('Validation/Validation_mAP', self.validation_accuracy, self.epoch_step)
    
    def saveTestingStatisticsObjectDetection(self):
        """Saves the statistice relevant for object detection"""
        evaluator = VOC_Evaluator()
        metrics = evaluator.GetPascalVOCMetrics(self.bounding_boxes,
                                                IOUThreshold=0.5,
                                                method=MethodAveragePrecision.EveryPointInterpolation)
        acc_AP = 0
        total_positives = 0
        for metricsPerClass in metrics:
            acc_AP += metricsPerClass['AP']
            total_positives += metricsPerClass['total positives']
        mAP = acc_AP / self.nr_classes
        self.testing_accuracy = mAP

        self.writer.add_scalar('Testing/Testing_Loss', self.testing_loss, self.epoch_step)
        self.writer.add_scalar('Testing/Testing_mAP', self.testing_accuracy, self.epoch_step)

    def getLearningRate(self):
        for param_group in self.optimizer.param_groups:
            return param_group['lr']

    def loadCheckpoint(self, filename):
        if os.path.isfile(filename):
            print("=> loading checkpoint '{}'".format(filename))
            checkpoint = torch.load(filename)
            self.epoch_step = checkpoint['epoch']
            self.model.load_state_dict(checkpoint['state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer'])
            print("=> loaded checkpoint '{}' (epoch {})".format(filename, checkpoint['epoch']))
        else:
            print("=> no checkpoint found at '{}'".format(filename))
    
    def loadCheckpointTest(self, filename):
        if os.path.isfile(filename):
            print("=> loading checkpoint '{}'".format(filename))
            checkpoint = torch.load(filename)
            self.epoch_step = checkpoint['epoch']
            self.model.load_state_dict(checkpoint['state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer'])
            print("=> loaded checkpoint '{}' (epoch {})".format(filename, checkpoint['epoch']))
        else:
            print("=> no checkpoint found at '{}'".format(filename))

    def saveCheckpoint(self):
        file_path = os.path.join(self.settings.ckpt_dir, 'model_step_' + str(self.epoch_step) + '.pth')
        torch.save({'state_dict': self.model.state_dict(), 'optimizer': self.optimizer.state_dict(),
                    'epoch': self.epoch_step}, file_path)

class SparseObjectDetModel(AbstractTrainer):
    def buildModel(self):
        """Creates the specified model"""
        self.model = FBSparseObjectDet(self.nr_classes, nr_input_channels=self.nr_input_channels,
                                       small_out_map=(self.settings.dataset_name == 'NCaltech101_ObjectDetection'))
        self.model.to(self.settings.gpu_device)
        self.model_input_size = self.model.spatial_size  # [191, 255]

        if self.settings.use_pretrained and (self.settings.dataset_name == 'NCaltech101_ObjectDetection' or
                                             self.settings.dataset_name == 'Prophesee'):
            self.loadPretrainedWeights()

    def loadPretrainedWeights(self):
        """Loads pretrained model weights"""
        print("-----------ENTRA---------------------")
        checkpoint = torch.load(self.settings.pretrained_sparse_vgg)
        try:
            pretrained_dict = checkpoint['state_dict']
        except KeyError:
            pretrained_dict = checkpoint['model']

        pretrained_dict_short = {}
        for k, v in pretrained_dict.items():
            if 'sparseModel.25' in k:
                break
            pretrained_dict_short[k] = v

        self.model.load_state_dict(pretrained_dict_short, strict=False)


    def test(self):
        
        self.loadCheckpointTest(self.settings.pretrained_sparse_vgg)
        
        self.pbar = tqdm.tqdm(total=self.nr_test_epochs, unit='Batch', unit_scale=True)
        self.resetTesting()
        self.model = self.model.eval()
        self.bounding_boxes = BoundingBoxes()
        loss_function = yoloLoss

        for i_batch, sample_batched in enumerate(self.test_loader):
            event, bounding_box, histogram = sample_batched

            # Convert spatial dimension to model input size
            histogram = torch.nn.functional.interpolate(histogram.permute(0, 3, 1, 2),
                                                        torch.Size(self.model_input_size))
            histogram = histogram.permute(0, 2, 3, 1)

            # Change x, width and y, height
            bounding_box[:, :, [0, 2]] = (bounding_box[:, :, [0, 2]] * self.model_input_size[1].float()
                                          / self.settings.width).long()
            bounding_box[:, :, [1, 3]] = (bounding_box[:, :, [1, 3]] * self.model_input_size[0].float()
                                          / self.settings.height).long()
            locations, features = self.denseToSparse(histogram)

            with torch.no_grad():
                model_output = self.model([locations, features, histogram.shape[0]])
                loss = loss_function(model_output, bounding_box, self.model_input_size)[0]
                detected_bbox = yoloDetect(model_output, self.model_input_size.to(model_output.device),
                                           threshold=0.7)
                detected_bbox = nonMaxSuppression(detected_bbox, iou=0.6)
                detected_bbox = detected_bbox.cpu().numpy()

            # Save validation statistics
            self.saveBoundingBoxesTest(bounding_box.cpu().numpy(), detected_bbox)

            batch_one_mask = locations[:, -1] == 0
            vis_locations = locations[batch_one_mask, :2]
            features = features[batch_one_mask, :]
            vis_detected_bbox = detected_bbox[detected_bbox[:, 0] == 0, 1:-2].astype(np.int)
                
            # Visualization
            image = visualizations.visualizeLocations(vis_locations.cpu().int().numpy(), self.model_input_size,
                                                      features=features.cpu().numpy(),
                                                      bounding_box=bounding_box[0, :, :].cpu().numpy(),
                                                      class_name=[self.object_classes[i]
                                                                      for i in bounding_box[0, :, -1]])
            image = visualizations.drawBoundingBoxes(image, vis_detected_bbox[:, :-1],
                                                     class_name=[self.object_classes[i]
                                                     for i in vis_detected_bbox[:, -1]],
                                                     ground_truth=False, rescale_image=False)
            
            path_name = os.path.join(self.settings.vis_dir, 'image_' + str(self.test_batch_step) + '.png')
            fig, ax = plt.subplots()
            ax.imshow(image.astype(np.float))
            ax.axis('off')
            fig.savefig(path_name)
            plt.close()

            self.pbar.set_postfix(ValLoss=loss.data.cpu().numpy())
            self.pbar.update(1)
            self.test_batch_step += 1
            self.testing_loss += loss

        self.testing_loss = self.testing_loss / float(self.test_batch_step)
        self.saveTestingStatisticsObjectDetection()

        self.pbar.close()
