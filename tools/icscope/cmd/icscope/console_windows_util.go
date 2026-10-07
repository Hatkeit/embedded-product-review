//go:build windows

package main

import (
	"syscall"
	"unsafe"
)

func unsafePtr(s string) unsafe.Pointer {
	p, _ := syscall.UTF16PtrFromString(s)
	return unsafe.Pointer(p)
}
