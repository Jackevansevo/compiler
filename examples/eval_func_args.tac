func square
params 1
param int x
t3 = x * x
return t3
endfunc
func main
t5 = 2 + 1
arg t5
t6 := call square
print t6
return 0
endfunc
