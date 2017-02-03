
import random 

number = random.randint(0,10)
#print(number)	

print("Guess the number:")
user_guess = int(raw_input())

if user_guess == number :
	
	print("You guess right")

else:
	
	print("You guess wrong")


print("Enter a number to know if it's even or odd")
number_2 = int(float (raw_input()))

if number_2%2 == 0 :
	print("Even number")
else :
	print("Odd number")

