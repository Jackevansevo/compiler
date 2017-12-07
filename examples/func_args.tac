func square
param int b
t3 = b * b
return t3
endfunc
func main
arg 5
t5 := call square
x := t5
print x
return 0
endfunc
