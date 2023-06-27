SECTIONS {
	.text 0x00000000 : { *(.text) }
	.data : { *(.data) }
	.bss  : { *(.bss) }
	.eh_frame : { *(.eh_frame) }
}

