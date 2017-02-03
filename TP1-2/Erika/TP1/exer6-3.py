import random

def pile(param1, param2, param3, param4):	
	return [param1, param2, param3, param4]


def empile(pila, elem):
	pila.append(elem)

def depile(pila):
	
	element = pila.pop(0)
	return element


stock = pile(random.randint(0,10), random.randint(0,30), random.randint(0,60), random.randint(0,80))
print(stock)
empile(stock, random.randint(0,100))
print(stock)

elem_depile = depile(stock)

print elem_depile