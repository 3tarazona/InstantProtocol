import random

def pile(param1, param2, param3, param4):	
	return [param1, param2, param3, param4]


def empile(pila, elem):
	pila.append(elem)

def depile(pila):
	element = pila.pop()
	return element


stock = pile(random.randint(0,10), random.randint(0,30), random.randint(0,60), random.randint(0,80))

empile(stock, random.randint(0,100))

elem_depile = depile(stock)



print elem_depile