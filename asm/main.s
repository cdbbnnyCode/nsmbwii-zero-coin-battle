	.section ".text"

/* subroutine: get current address */
/* inputs: none, returns: r3=address of the instruction after the subroutine call */
get_curr_address:
	mflr  %r3
	blr

/* subroutine: get total coins */
/* inputs: r3=results data pointer r4=player index, returns: r3=total coins */
get_total_coins:
	stwu  %r1, -0x18(%r1)
	stw   %r0, 0x8(%r1)
	stw   %r5, 0xc(%r1)
	stw   %r6, 0x10(%r1)
	stw   %r7, 0x14(%r1)
	
	slwi  %r5, %r4, 2    /* r5 = r4*4 */
	addi  %r5, %r5, 0x28 /* r5 = &baseCoins[r4] */
	lwzx  %r0, %r3, %r5  /* r0 = baseCoins[r4] */

	addi  %r5, %r5, 0x20 /* r5 = &bonusCoins[r4] */
	lwzx  %r6, %r3, %r5  /* r6 = bonusCoins[r4] */
	add   %r0, %r0, %r6  /* r0 += bonusCoins[r4] */
	
	addi  %r5, %r3, 0x58 /* r5 = &starCoins */
	lbzx  %r6, %r5, %r4  /* r6 = starCoins[r4] */
starcoin_loop:
	andi. %r7, %r6, 1    /* r7 = r6 & 0x1 */
	beq   starcoin_no_add
	mr    %r7, %r0       /* add using r7 because ppc can't addi with r0 as an operand */
	addi  %r7, %r7, 10   /* add 10 coins if the star coin is present */
	mr    %r0, %r7 
starcoin_no_add:
	srwi. %r6, %r6, 1    /* r6 >>= 1 */
	bne+  starcoin_loop  /* loop until r6 == 0 */

	mr    %r3, %r0

	lwz   %r0, 0x8(%r1)
	lwz   %r5, 0xc(%r1)
	lwz   %r6, 0x10(%r1)
	lwz   %r7, 0x14(%r1)
	addi  %r1, %r1, 0x18
	blr

	.globl calc_penalties
calc_penalties: /* patch over 807a53e8: li r29, 0x1 */
	/* save: r0 r3 r4 r5 r6 r7 r8 r30 r31 LR */
	stwu  %r1, -0x2c(%r1)
	stw   %r0, 0x8(%r1)
	
	/* save LR */
	mflr  %r0
	stw   %r0, 0x30(%r1)

	stw   %r3, 0xc(%r1)
	stw   %r4, 0x10(%r1)
	stw   %r5, 0x14(%r1)
	stw   %r6, 0x18(%r1)
	stw   %r7, 0x1c(%r1)
	stw   %r8, 0x20(%r1)
	stw   %r31, 0x24(%r1)
	stw   %r30, 0x28(%r1)

	bl    get_curr_address
calc_penalties_base_addr:
	li    %r0, calc_penalties_base_addr
	sub   %r7, %r3, %r0 /* r7 = address - label offset */

	/* calculated max lives */
	li    %r0, 0
	/* resultsData pointer in r25 */
	mr    %r3, %r25
	/* player indices (present + 16) in r28 */
	addi  %r4, %r28, -0x10
	/* counter */
	li    %r5, 0
maxlives_loop:
	/* skip if this player is not present */
	lwz   %r6, 0(%r4)
	cmpwi %r6, 0
	beq-  maxlives_loop_end

	lwz   %r6, 0x8(%r3) /* r6 = lives */
	cmpw  %r6, %r0
	ble   no_update_maxlives
/* if r6 > r0, update max lives */
	mr    %r0, %r6
no_update_maxlives:
maxlives_loop_end:
	/* increment pointers and counter */
	addi  %r3, %r3, 4
	addi  %r4, %r4, 4
	addi  %r5, %r5, 1
	cmpwi %r5, 4
	blt+  maxlives_loop

/* part 2: add bonus (penalty) coins */
	/* move pointers back to the beginning */
	subi  %r3, %r3, 0x10
	subi  %r4, %r4, 0x10
	li    %r5, 0
penalty_loop:
	/* skip if this player is not present */
	lwz   %r6, 0(%r4)
	cmpwi %r6, 0
	beq-  penalty_loop_end

	lwz   %r6, 0x8(%r3) /* r6 = lives */
	sub   %r6, %r0, %r6 /* r6 = maxlives - lives */

	li    %r8, penalty_value /* load the offset from r7 to our word */
	lwzx  %r8, %r7, %r8 /* r8 = number of penalty coins */
	mullw %r6, %r6, %r8 /* r6 = total penalty coins */

	mr    %r31, %r3
	mr    %r30, %r4
	/* set up parameters (I'm not an optimizing compiler) */
	mr    %r3, %r25
	mr    %r4, %r5
	bl    get_total_coins
	
	li    %r8, target_coins
	lwzx  %r8, %r7, %r8 /* r8 = target coin count */
	cmpw  %r3, %r7 /* compare total coins to target coins */
	bgt+  no_inv_penalty
	neg   %r6, %r6 /* r6 = -r6, add negative penalty if below the target */
no_inv_penalty:
	/* restore our temporarily saved registers */
	mr    %r3, %r31
	mr    %r4, %r30

	lwz   %r8, 0x48(%r3) /* r8 = bonus coins */
	add   %r8, %r8, %r6 /* add penalties */
	stw   %r8, 0x48(%r3)

penalty_loop_end:
	/* increment pointers/counters */
	addi  %r3, %r3, 4
	addi  %r4, %r4, 4
	addi  %r5, %r5, 1
	cmpwi %r5, 4
	blt+  penalty_loop
	
	/* restore saved state */
	lwz   %r0, 0x30(%r1) /* saved LR */
	mtlr  %r0

	lwz   %r0, 0x8(%r1)
	lwz   %r3, 0xc(%r1)
	lwz   %r4, 0x10(%r1)
	lwz   %r5, 0x14(%r1)
	lwz   %r6, 0x18(%r1)
	lwz   %r7, 0x1c(%r1)
	lwz   %r8, 0x20(%r1)
	lwz   %r31, 0x24(%r1)
	lwz   %r30, 0x28(%r1)
	addi  %r1, %r1, 0x2c
	li    %r29, 0x1 /* original patched-over instruction */
	blr

/* ----------------------------------------------------------------------- */

	.globl modify_ranking_coins
modify_ranking_coins:
	/* results screen data pointer in r3 */
	stwu  %r1, -0x28(%r1)
	stw   %r0, 0x8(%r1)

	mflr  %r0
	stw   %r0, 0x2c(%r1)

	stw   %r3, 0x10(%r1)
	stw   %r4, 0x14(%r1)
	stw   %r5, 0x18(%r1)
	stw   %r6, 0x1c(%r1)
	stw   %r7, 0x20(%r1)
	stw   %r8, 0x24(%r1)

	bl    get_curr_address
modify_ranking_base_addr:
	li    %r0, modify_ranking_base_addr
	sub   %r5, %r3, %r0 /* r5 = address - label offet */

	lwz   %r3, 0x10(%r1) /* get our r3 back */

	/* r8 = target coins */
	li    %r0, target_coins
	lwzx  %r8, %r5, %r0

	/* cards @ 0x7bc + r3 */
	/* total_coins @ card[0x4] */
	/* present (byte) @ card[0x29] */
	/* card size = 0x3c, total = 0xf0 bytes */
	addi  %r4, %r3, 0x7bc /* current player card pointer */
	li    %r6, 0
	li    %r0, 0
max_coins_loop:
	/* skip if not present */
	lbz   %r7, 0x29(%r4)
	cmpwi %r7, 0
	beq- max_coins_loop_end

	lwz   %r7, 0x4(%r4) /* r7 = total coins */
	sub.  %r7, %r7, %r8 /* r7 -= r8 */
	bge+  no_inv_diff_coins
	/* absolute value: invert diff_coins if it is less than 0 */
	neg   %r7, %r7
no_inv_diff_coins:
	
	/* temporarily store the diff coins as total coins */
	stw   %r7, 0x4(%r4)

	cmpw  %r7, %r0
	ble   no_update_max_coins
	/* update maximum coins if r7 > max */
	mr    %r0, %r7
no_update_max_coins:
max_coins_loop_end:
	addi  %r4, %r4, 0x3c
	addi  %r6, %r6, 1
	cmpwi %r6, 4
	bne+  max_coins_loop

	subi  %r4, %r4, 0xf0 /* reset r4 */
	li    %r6, 0
recalc_coins_loop:
	/* skip if not present */
	lbz   %r7, 0x29(%r4)
	cmpwi %r7, 0
	beq- recalc_coins_loop_end

	lwz   %r7, 0x4(%r4) /* get diff coins */
	sub   %r7, %r0, %r7 /* r7 = max - diff coins */
	stw   %r7, 0x4(%r4)
recalc_coins_loop_end:
	addi  %r4, %r4, 0x3c
	addi  %r6, %r6, 1
	cmpwi %r6, 4
	bne+ recalc_coins_loop

	li    %r6, swap_check_addr
	lwzx  %r0, %r5, %r6
	mtctr %r0
	bctrl /* jump to the swap check since we overwrote the branch */

	lwz   %r0, 0x2c(%r1)
	mtlr  %r0
	lwz   %r0, 0x8(%r1)
	lwz   %r4, 0x14(%r1)
	lwz   %r5, 0x18(%r1)
	lwz   %r6, 0x1c(%r1)
	lwz   %r7, 0x20(%r1)
	lwz   %r8, 0x24(%r1)
	addi  %r1, %r1, 0x28
	blr

/* -------------------------------------------------------------------- */

	.globl patch_init_lives
patch_init_lives:
	/* called by the REL prolog */
	stwu %r1, -0xc(%r1)
	stw  %r3, 0x4(%r1)
	stw  %r4, 0x8(%r1)

	/* load our target address, 800e18dc */
	lis  %r3, 0x800e
	addi %r3, %r3, 0x18dc

	/* load our instruction data 38 60 00 xx */
	lis  %r4, 0x3860
	addi %r4, %r4, 50    /* number of lives */

	/* do the patch */
	stw  %r4, 0(%r3)

	/* flush caches */
	dcbf 0,%r3
	sync
	icbi 0,%r3
	isync

	/* clean up */
	lwz  %r3, 0x4(%r1)
	lwz  %r4, 0x8(%r1)
	addi %r1, %r1, 0xc

	lwz  %r0, 0x14(%r1)
	blr

/* data/constants */
penalty_value:
	.int 10 /* number of penalty coins per death */
target_coins:
	.int 0  /* target coin count */
swap_check_addr:
	.int 0x807a4be0



