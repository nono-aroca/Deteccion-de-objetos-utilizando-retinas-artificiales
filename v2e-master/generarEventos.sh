#!/bin/bash

#Ejemplo de uso: bash -i generarEventos.sh video1 video2

let CONTADOR=0

for i in "$@"
do
	let CONTADOR=$CONTADOR+1
	conda activate v2e
	python v2e.py -i input/$i.avi --overwrite --timestamp_resolution=.003 --auto_timestamp_resolution=False --dvs_exposure duration 0.005 --output_folder=output/$i --overwrite --pos_thres=.15 --neg_thres=.15 --sigma_thres=0.03 --output_width=854 --output_height=480 --cutoff_hz=15
	echo "Vídeo $CONTADOR: $i completado"
	conda deactivate
	conda activate ros
	python2 eventsToBag.py output/$i/dvs-video.avi output/$i/$i.bag
	conda deactivate
	conda activate v2e
	echo "Generado archivo bag correctamente"
	mv output/$i/v2e-dvs-events.txt output/$i/$i.txt 
done
