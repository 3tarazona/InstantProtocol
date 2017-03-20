import threading

def hello(s):
    print s

h="hello world"
t = threading.Timer(10.0, hello, [h])
t.start()
print "Hi"
i=10
i=i+20
print i
#t.cancel()
