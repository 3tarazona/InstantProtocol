
	
import random

lista = [random.randint(0,100),random.randint(0,100),random.randint(0,100), random.randint(0,100), random.randint(0,100)]
lista_sorted = sorted(lista)
print(lista_sorted)

lista_sorted.append(12)
print(lista_sorted)

lista_sorted.append(random.randint(0,100))
print(sorted(lista_sorted))
print(lista_sorted[1:])

