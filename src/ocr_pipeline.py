# ocr_pipeline.py

import cv2                           # libreria OpenCV para vision por computador
from PIL import Image                # para imagen
import numpy as np                   # numerical python
import pandas as pd                  # dataframe (datos parametros)
from google_speech import Speech     # para hablar
from googletrans import Translator   # para traducir
import speech_recognition as sr      # reconocimiento de voz
import time                          # tiempo
import os                            # sistema, directorios
from keras.models import load_model  # carga modelo de keras
import tensorflow as tf              # quitar texto de tensorflow
tf.logging.set_verbosity(tf.logging.ERROR)
import pymongo                       # mongodb, para llamada a atlas
from mamba_mesh import *
from darksky import forecast
from datetime import date, timedelta
import re



def token(token):                                   # lectura de txt, token
    with open(token, 'r') as f:
        t=f.readlines()[0].split('\n')[0]
    return t


cliente=pymongo.MongoClient('mongodb+srv://Yonatan:{}@mambacluster-v9uol.mongodb.net/test?retryWrites=true&w=majority'.format(token('mongoatlas.txt')))
db=cliente.test
original=db.original      # colecciones
traduccion=db.traduccion
trigger=db.trigger
cursor=original.find()    # cursores
cursor2=traduccion.find()
cursor3=trigger.find()



def captura():                                      # funcion captura video por webcam (para sacar foto)
	cam=cv2.VideoCapture(0)                         # inicia captura
	while True:           
		ret, frame=cam.read()                       # lee la camara frame a frame
		cv2.imshow("Captura de imagen", frame)      # muestra imagen por pantalla con nombre
		if ret==False:                              # ret=retorno (booleano)
			break
		key=cv2.waitKey(1)                          # espera por OnClick de una tecla
		if key%256==27:                             # presiona escape para salir
			break
		elif key%256==32:                           # presiona espacio para capturar
			img_name="captura.png"                  # nombra png
			cv2.imwrite(img_name, frame)            # guarda la imagen
			print("{} guardada".format(img_name))
			break
	cam.release()                                   # cierra la pantalla de captura
	cv2.destroyAllWindows()                         # destruye todas las ventanas de imagen



def contraste():                                    # funcion para pasar imagen a blanco y negro 
	image=cv2.imread('captura.png')                 # lee la captura de imagen         
	im=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)       # pasa a escala de grises
	im=(255-im)                                     # foto en negativo
	umbral=170
	img=np.zeros(shape=im.shape)                    # pasa a blanco y negro puros (umbral en 170)
	for i in range(im.shape[0]):
		for j in range(im.shape[1]):
			if im[i][j]>umbral: img[i][j]=255
			else: img[i][j]=0
	#cv2.imshow('img', img)                          # muestra la imagen
	cv2.imwrite('b&w.png', img)                     # guarda imagen en blanco y negro
	cv2.waitKey(1)                                  # espera por tecla (si se comenta esta linea no se muestra la imagen)                


  
def contorno():                                     # funcion captura de contorno, captura letras
	umbral_fino=10                                  # umbral fino para deteccion de contornos
	image=cv2.imread('b&w.png')                     # lee la imagen
	im=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)       # pasa a grises
	im=(255-im)                                     # pasa a negativo
	thresh=cv2.adaptiveThreshold(im, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)      # umbral adaptativo
	rect_kernel=cv2.getStructuringElement(cv2.MORPH_RECT, (30, 10))                                          # elemento estructural (rectangular) 
	threshed=cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, rect_kernel)                                          # transformacion morfologica
	contorno, _ =cv2.findContours(threshed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)                      # encuentra los contornos
	s_contorno=sorted(contorno, key=lambda x: cv2.boundingRect(x)[1]+cv2.boundingRect(x)[0]*image.shape[1])  # ordena por orden lateral (y+xh)
	idx=0
	for cnt in s_contorno:                                   # contornos
		idx+=1
		x, y, w, h=cv2.boundingRect(cnt)
		roi=im[y:y+h, x:x+w]                                 # region de interes
		if h<umbral_fino or w<umbral_fino:
			continue
		cv2.imwrite(str(idx) + '.png', roi)
		cv2.rectangle(im, (x, y), (x+w, y+h), (200, 0, 0), 2)
	#cv2.imshow('imagen B-N', im)
	cv2.waitKey(1)
	return idx



def normalizador(X):                                # normalizador de los datos de letra
    X_media=X.mean()               
    X_std=X.std()                  
    X=(X-X_media)/X_std            
    X=np.insert(X,0,1)             
    return X



def f(X,a):                                         # funcion logistica, sigmoide, funcion del modelo, con z=X*alfa, el producto escalar
    return 1.0/(1.0+np.exp(-np.dot(X,a)))           # Boltzmann con pivote, alfa[i]=0



def interpreta_softmax(idx):                        # funcion evaluacion modelo softmax
	A_opt=pd.read_csv('../input/alfa-letras.csv').values  # parametros salida softmax
	resultado=''
	
	alfabeto={0:'0', 1:'1', 2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9',
		      10:'A', 11:'B', 12:'C', 13:'D', 14:'E', 15:'F', 16:'G', 17:'H', 18:'I', 19:'J',
	          20:'K', 21:'L', 22:'M', 23:'N', 24:'O', 25:'P', 26:'Q', 27:'R', 28:'S', 29:'T',
	          30:'U', 31:'V', 32:'W', 33:'X', 34:'Y', 35:'Z',
	          36:'a', 37:'b', 38:'c', 39:'d', 40:'e', 41:'f', 42:'g', 43:'h', 44:'i', 45:'j',
	          46:'k', 47:'l', 48:'m', 49:'n', 50:'o', 51:'p', 52:'q', 53:'r', 54:'s', 55:'t',
	          56:'u', 57:'v', 58:'w', 59:'x', 60:'y', 61:'z'}
	
	alfabeto_M={1:'A', 2:'B', 3:'C', 4:'D', 5:'E', 6:'F', 7:'G', 8:'H', 9:'I', 10:'J',
	            11:'K', 12:'L', 13:'M', 14:'N', 15:'O', 16:'P', 17:'Q', 18:'R', 19:'S', 20:'T',
	            21:'U', 22:'V', 23:'W', 24:'X', 25:'Y', 26:'Z'}
	          
	for i in range(idx):
		nombre=str(i+1)+'.png'           # nombre de la imagen
		img=cv2.imread(nombre)           # lee imagen
		shape=img.shape                  # creo un marco blanco, zoom out
		w=shape[1]
		h=shape[0]
		ancho_marco=h+20,w+20,3                                
		datos=np.zeros(ancho_marco,dtype=np.uint8)
		cv2.rectangle(datos,(0,0),(w+20,h+20),(255,255,255),30)
		datos[10:h+10,10:w+10]=img 
		datos=cv2.cvtColor(datos,cv2.COLOR_BGR2GRAY)
		datos=np.array(Image.fromarray(datos).resize((28,28)))
		#datos=misc.imresize(datos, (28, 28))
		datos=(255-datos)
		datos=datos.reshape(784,)
		datos=normalizador(datos)
		n_etiq=A_opt.shape[1]
		probs=np.zeros((n_etiq,2)) 
		for n in range(n_etiq):
			alfa=A_opt[:,n]               # parametros de softmax
			probs[n,0]=n                  # evaluacion de la prediccion
			probs[n,1]=f(datos,alfa)      
		probs=probs[probs[:,1].argsort()[::-1]]	 # primero el de mas probabilidad
		etiqueta=int(probs[0,0])                 # prediccion, etiqueta de la letra
		resultado+=alfabeto_M[etiqueta]          # busca en alfabeto
	
	for i in range(idx):        # borra imagenes
		nombre=str(i+1)+'.png' 
		os.remove(nombre) 
	os.remove('captura.png')
	os.remove('b&w.png')	                          
	return resultado



def interpreta_cnn(idx):                            # funcion evaluacion modelo cnn
	modelo=load_model('../input/modelo_cnn_letras.h5')   # modelo cnn
	resultado=''
	alfabeto={0:'0', 1:'1', 2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9',
		      10:'A', 11:'B', 12:'C', 13:'D', 14:'E', 15:'F', 16:'G', 17:'H', 18:'I', 19:'J',
	          20:'K', 21:'L', 22:'M', 23:'N', 24:'O', 25:'P', 26:'Q', 27:'R', 28:'S', 29:'T',
	          30:'U', 31:'V', 32:'W', 33:'X', 34:'Y', 35:'Z',
	          36:'a', 37:'b', 38:'c', 39:'d', 40:'e', 41:'f', 42:'g', 43:'h', 44:'i', 45:'j',
	          46:'k', 47:'l', 48:'m', 49:'n', 50:'o', 51:'p', 52:'q', 53:'r', 54:'s', 55:'t',
	          56:'u', 57:'v', 58:'w', 59:'x', 60:'y', 61:'z'}
	
	alfabeto_M={1:'A', 2:'B', 3:'C', 4:'D', 5:'E', 6:'F', 7:'G', 8:'H', 9:'I', 10:'J',
	            11:'K', 12:'L', 13:'M', 14:'N', 15:'O', 16:'P', 17:'Q', 18:'R', 19:'S', 20:'T',
	            21:'U', 22:'V', 23:'W', 24:'X', 25:'Y', 26:'Z'}
	
	try:
		for i in range(idx):
			nombre=str(i+1)+'.png'           # nombre de la imagen
			img=cv2.imread(nombre)           # lee imagen
			datos=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
			datos=np.array(Image.fromarray(datos).resize((28,28)))
			datos=(255-datos)/255              # normliza y negativo imagen
			datos=datos.reshape(1,28,28,1)     # redimensiona para input
			pred=modelo.predict_classes(datos) # prediccion
			resultado+=alfabeto_M[pred[0]]  
			
		for i in range(idx):        # borra imagenes
			nombre=str(i+1)+'.png' 
			os.remove(nombre) 	  
		os.remove('captura.png')
		os.remove('b&w.png')	   
		return resultado
		
	except: return 'No se ha reconocido la imagen, ha fallado el ordenado de open c v'



def habla(texto, leng='es'):                        # funcion para speech
	print(texto)
	voz=Speech(texto, leng)
	return voz.play() 



def traduce(texto, leng='en'):                      # funcion para traducir
	traductor=Translator()
	traduccion=traductor.translate(texto, dest=leng).text
	pronunciacion=traductor.translate(texto, dest=leng).pronunciation
	return traduccion



def clima():
	MADRID=40.4165000, -3.7025600
	dia_semana=date.today()
	semana=[]
	with forecast('2e27c520174cdbb07f95a6ecf01fe848', *MADRID) as madrid:
		for dia in madrid.daily:
			dia=dict(dia=date.strftime(dia_semana, '%a'),
					 sum=dia.summary,
					 tempMin=round((dia.temperatureMin-32)/1.8),
					 tempMax=round((dia.temperatureMax-32)/1.8)
					   )
			semana.append(dia)
			dia_semana+=timedelta(days=1)
	return [semana[0]['sum'], semana[0]['tempMin'], semana[0]['tempMax'], semana[1]['sum'], semana[1]['tempMin'], semana[1]['tempMax']]



def mongo_escribe(ori, trad):                       # llamada a atlas
	cliente=pymongo.MongoClient('mongodb+srv://Yonatan:{}@mambacluster-v9uol.mongodb.net/test?retryWrites=true&w=majority'.format(token('mongoatlas.txt')))
	db=cliente.test  # base de datos

	try:
		print('MongoDB version is {}'.format(cliente.server_info()['version']))
	except pymongo.errors.OperationFailure as error:
		print(error)
		quit(1)

	original=db.original      # colecciones
	traduccion=db.traduccion

	cursor=original.find()    # cursores
	cursor2=traduccion.find()

	cont=0                   # comprueba si existe el original, si no añadela
	for item in cursor:
		if item['palabra']==ori: cont+=1
	if cont==0 and ori!=trad: original.insert_one({'palabra':ori})

	cont2=0                  # comprueba si existe la traduccion, si no añadela
	for item2 in cursor2:
		if item2['palabra']==trad: cont2+=1
	if cont2==0 and ori!=trad: traduccion.insert_one({'palabra':trad})



def activacion():                                   # graba audio
	r=sr.Recognizer()
	with sr.Microphone() as s:
		print('Desactivada...')
		r.adjust_for_ambient_noise(s)
		audio=r.listen(s)
	
	datos=''  # reconocimiento de voz
	try:      # Usa API key por defecto, para usar otra: `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
		datos=r.recognize_google(audio, language='es-ES')
	except sr.UnknownValueError:
		print("Google Speech Recognition no ha podido reconocer el audio.")
	except sr.RequestError as e:
		print("No hay respuesta desde el servicio de Google Speech Recognition; {0}".format(e))
	return datos



def escucha():                                      # graba audio
	r=sr.Recognizer()
	with sr.Microphone() as s:
		print('¡Cuentame!')
		#habla('cuentame')
		r.adjust_for_ambient_noise(s)
		audio=r.listen(s)
	
	datos=''  # reconocimiento de voz
	try:      # Usa API key por defecto, para usar otra: `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
		datos=r.recognize_google(audio, language='es-ES')
		print('Has dicho: ' + datos)
	except sr.UnknownValueError:
		print("Google Speech Recognition no ha podido reconocer el audio.")
		trigger.update_one({"a":'0'}, {"$set":{"a": "1"}})
		habla('Disculpa, no te he entendido.')
		trigger.update_one({"a":'1'}, {"$set":{"a": "0"}})
	except sr.RequestError as e:
		print("No hay respuesta desde el servicio de Google Speech Recognition; {0}".format(e))
	return datos



def mamba(datos):                                   # asistente Mamba 
	cliente=pymongo.MongoClient('mongodb+srv://Yonatan:{}@mambacluster-v9uol.mongodb.net/test?retryWrites=true&w=majority'.format(token('mongoatlas.txt')))
	db=cliente.test
	original=db.original
	traduccion=db.traduccion
	cursor=original.find()
	cursor2=traduccion.find()
	
	idioma='en'   # idioma traduccion
	
	if 'captura' in datos:
		try:
			captura()
			contraste()
			idx=contorno()
			#palabra=interpreta_softmax(idx).lower()        # con modelo softmax
			palabra=interpreta_cnn(idx).lower()             # con modelo convolucional
			#print (palabra)
			trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
			habla(palabra, leng='es')
			trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
			traduccion=(traduce(palabra.lower(), leng=idioma))
			#print (traduccion)
			habla(traduccion, leng=idioma)
			mongo_escribe(palabra, traduccion)
		
		except:
			trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
			habla('No se ha reconocido la imagen', leng='es')
			trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
	
	
	if 'originales' in datos:
		cursor=original.find()
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		for item in cursor:
			habla(item['palabra'])
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
		
		
	if 'traducciones' in datos:
		cursor2=traduccion.find()
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		for item in cursor2:
			habla(item['palabra'], leng=idioma)
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})	
	
	
	if 'gracias' in datos:
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla('gracias a ti, alegre')
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
		flag=True
		return flag
	
	
	if 'cómo estás' in datos:
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla('estoy bien, gracias')
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
		
		
	if 'qué hora es' in datos:
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla(time.strftime("%H:%M:%S"))
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
	
	
	if 'Siri' in datos:
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla('siri es una manzana mordida y alexa es una amazona')
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
		
		
	if 'te pones' in datos:
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla('eres tu el que pregunta')
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
		
	
	if 'tiempo' in datos:
		c=clima()
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla(re.sub('Borrar', 'Despejado', traduce(c[0], leng='es')))
		habla('temperatura mínima '+str(c[1])+' grados')
		habla('temperatura máxima '+str(c[2])+' grados')
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
	
	
	if 'mañana' in datos:
		c=clima()
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla(re.sub('Borrar', 'Despejado', traduce(c[3], leng='es')))
		habla('temperatura mínima '+str(c[4])+' grados')
		habla('temperatura máxima '+str(c[5])+' grados')
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
	
	
	if 'chiste' in datos:
		trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
		habla('van dos soldados en una moto y....no se cae ninguno porque van soldados')
		trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
		

	

def exe():                                          # funcion de ejecucion
	while 1:
		trigger_word=activacion()     # palabra activacion
		if trigger_word=='escucha':
			trigger.update_one({"a":'0'}, {"$set":{"a":"1"}})
			habla('Hola. Cuentame.')
			trigger.update_one({"a":'1'}, {"$set":{"a":"0"}})
			while 1:
				datos=escucha()
				flag=mamba(datos)
				if flag: break






































