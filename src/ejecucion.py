# ejecucion.py


from ocr_pipeline import *



if __name__=='__main__':    # inicializa el asistente
	habla("Hola. Soy Mamba, ¿que puedo hacer por ti?")
	while 1:
		datos=escucha()
		flag=mamba(datos)
		if flag: break





