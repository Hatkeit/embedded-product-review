package main

import "syscall"

// Korean Windows consoles default to code page 949; switch to UTF-8 so the
// status messages are readable.
func init() {
	k := syscall.NewLazyDLL("kernel32.dll")
	k.NewProc("SetConsoleOutputCP").Call(65001)
	k.NewProc("SetConsoleCP").Call(65001)
	k.NewProc("SetConsoleTitleW").Call(uintptr(unsafePtr("ICScope")))
}
