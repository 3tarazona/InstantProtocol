


print("Indiquez-vous quel range vous voulez la suite de Fibonacci?")
lim = int(raw_input())
f=[]
i=0
while len(f) < 2 or (f[i-1] + f[i-2])< lim:
	if len(f) < 2:
		f.append(i)
	else :
		f.append(f[i-1] + f[i-2])
	i+=1
	print(f)
