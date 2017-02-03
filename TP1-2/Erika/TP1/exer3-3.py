import math

lista = []
i = 0
exit1= "q"
exit2= "quit"

lim = raw_input("Entre l'element numero %d de la suite\n" %i )
while lim != exit1 and lim  != exit2		:
	lista.append(float(lim))
	#print(lista)
	i += 1
	
	moyenne= sum(lista)/i
	print("La Moyenne c'est: %f " %moyenne)
	lim = raw_input("Entre l'element numero %d de la suite\n" %i)
	



