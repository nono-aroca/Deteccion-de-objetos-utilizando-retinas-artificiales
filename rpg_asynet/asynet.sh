#!/bin/bash

#Ejemplo de uso: sh asynet.sh opcion

if [ $# -eq 1 ]
then
	if [ $1 -eq 0 ]
	then
		echo "Entrenamos el modelo"
		python train.py --settings_file config/settings.yaml
	elif [ $1 -eq 1 ]
	then
		echo "Entrenamos el modelo y hacemos inferencia con los mejores pesos obtenidos tras el entrenamiento"
		python train_and_test.py --settings_file config/settings.yaml
	elif [ $1 -eq 2 ]
	then
		echo "Hacemos inferencia salvando las estadísticas obtenidas en ella"
		python test_con_estadisticas.py --settings_file config/settings.yaml
	elif [ $1 -eq 3 ]
	then
		echo "Hacemos inferencia sin salvar las estadísticas obtenidas en ella"
		python test_sin_estadisticas.py --settings_file config/settings.yaml
	elif [ $1 -eq 4 ]
	then
		echo "Hacemos inferencia sobre mis datos teniendo en cuenta solo los primeros eventos generados"
		python test_mis_datos_primeros_eventos.py --settings_file config/settings.yaml
	elif [ $1 -eq 5 ]
	then
		echo "Hacemos inferencia sobre mis datos teniendo en cuenta todos los eventos generados"
		python test_mis_datos_todos_eventos.py --settings_file config/settings.yaml
	elif [ $1 -eq 6 ]
	then
		echo "Hacemos inferencia sobre mis datos teniendo en cuenta todos los eventos generados y creando un vídeo al final"
		python test_mis_datos_todos_eventos_con_video.py --settings_file config/settings.yaml
	else
		echo "Funcionamiento: sh asynet.sh opcion"
		echo "Opciones: 0: entrenamiento, 1: entrenamiento e inferencia, 2: inferencia salvando estadísticas, 3: inferencia sin salvar estadísticas, 4: inferencia sobre mis datos considerando solo los primeros eventos generados de cada archivo, 5: inferencia sobre mis datos considerando todos los eventos, 6: inferencia sobre mis datos considerando todos los eventos y generando un vídeo al final"
	fi
else
	echo "Funcionamiento: sh asynet.sh opcion"
	echo "Opciones: 0: entrenamiento, 1: entrenamiento e inferencia, 2: inferencia salvando estadísticas, 3: inferencia sin salvar estadísticas, 4: inferencia sobre mis datos considerando solo los primeros eventos generados de cada archivo, 5: inferencia sobre mis datos considerando todos los eventos, 6: inferencia sobre mis datos considerando todos los eventos y generando un vídeo al final"
fi
