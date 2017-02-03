import random 

number = random.randint(0,100)
	
user_guess = None
while number != user_guess :
	
	print("Guess the number:")
	user_guess = int(raw_input())

	if user_guess == number :
		
		print("Vous avez gagne")
		
	elif user_guess < number:
		
		print("Plus grand ")

	elif user_guess > number:
		
		print("Plus petit ")

		