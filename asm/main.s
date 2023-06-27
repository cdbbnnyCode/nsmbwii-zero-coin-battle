	.section ".text"

	.globl main
main:
	/* setup stack, save *everything* because we're not actually supposed to be here */
	/* Stack layout:
	 *   00 : saved SP
	 *   04 : r3
 	 *   08 : r4
	 *   0c : r5
	 *   10 : r23
	 *   14 : r25
	 *   18 : r26
	 *   1c : r27
	 *   20 : r28
	 *   24 : r30
	 *   28 : r31
	 *   2c : <- prev SP location (saved SP)
	 *   30 : LR
         */
	stwu %r1, -0x2c(%r1) /* create the stack frame with 0x2c bytes of space */
	mflr %r0
	stw  %r0,  0x30(%r1)
	stw  %r3,  0x04(%r1)
	stw  %r4,  0x08(%r1)
	stw  %r5,  0x0c(%r1)
	stw  %r23, 0x10(%r1)
	stw  %r25, 0x14(%r1)
	stw  %r26, 0x18(%r1)
	stw  %r27, 0x1c(%r1)
	stw  %r28, 0x20(%r1)
	stw  %r30, 0x24(%r1)
	stw  %r31, 0x28(%r1)
	
	/* actual code now */
	/* Settings */
	li   %r31, 10      /* number of coins per death penalty */
	li   %r30, 0      /* target coin count */
	/* Scoring:
	 * find maximum lives
	 * calculate total coins for each player = base + bonus + 10*star
	 * calculate diff coins for each player = abs(total - diff)
	 * find maximum and minimum diff coins
	 * apply minimum-coins rule: coins = max - coins
	 * add minimum diff to everyone
	 */
	/* get a base pointer here so that we can relatively reference our temp data */
	/* this isn't really necessary but I don't want to rewrite the linker script if the addr changes */
	bl base_ptr
base_ptr:
	mflr %r0 /* r0 now points to the base pointer */
	li %r24, base_ptr
	sub  %r0, %r0, %r24 /* r0 now points to the beginning of our code */
	li %r24, diff_coins /* offset from r0 to diff_coins */
	add  %r0, %r0, %r24 /* r0 now points to diff_coins */
	/* find diff coins for everyone
	 * - r3 = temp
    	 * - r4 = player index
	 * - r5 = maximum lives
	 * - r6 = secondary temp value for reading data
	 * - r7 = pointer to diff_coins plus 4*index
	 * - r23 = pointer to the present array in player data (80354e50)
	 * - r25 = pointer to resultsData from the function we patched into
	 * - r26 = resultsData pointer plus 4*index
	 * - r27 = resultsData pointer plus 1*index (for star coins)
	 * - r28 = 1 (for calculating r6), star coin mask
	 * - r29 = star coin mask result
	 */
	li   %r4,  0
	li   %r5,  0
	mr   %r7,  %r0
	lis  %r23, 0x8035
	addi %r23, %r23, 0x4e50
	mr   %r26, %r25
	mr   %r27, %r25
	li   %r28, 1
diff_coin_loop:
	lwz  %r6,  0(%r23)       /* check if the player we're looking at is present */
	cmpwi %r6, 0
	beq  diff_coin_loop_end  /* if r6 == 0, skip to the end of the loop */

	lwz  %r3,  0x08(%r26)    /* get player lives */
	cmpw %r3,  %r5           /* check if greater than current maximum */
	ble  no_update_max_lives

	mr   %r5,  %r3
no_update_max_lives:
	li   %r3,  0 /* initialize total coin count to 0 */
	lbz  %r6,  0x58(%r27) /* star coins */
starcoin_loop:
	and  %r29, %r6, %r28  /* r29 = (has coin) */
	add  %r3,  %r3, %r29  /* r3 += (has coin) */
	srwi. %r6,  %r6, 1    /* shift to the next coin, update CR */
	bne starcoin_loop

	mulli %r3, %r3, 10

	lwz  %r6,  0x28(%r26) /* base coins */
	add  %r3,  %r3, %r6   /* r3 += base coins */
	lwz  %r6,  0x48(%r26) /* bonus coins */
	add  %r3,  %r3, %r6   /* r3 += bonus coins */

	stw  %r3,  0x28(%r26) /* save total to base coins */
	
	sub. %r3,  %r3, %r30  /* subtract target, update CR so we can check if the result is negative */
	bge  no_abs_diffcoins

	neg  %r3,  %r3 /* take the absolute value */
no_abs_diffcoins:
	stw  %r3,  0(%r7)

diff_coin_loop_end:
	/* increment everything */
	addi %r4,  %r4, 1
	addi %r7,  %r7, 4
	addi %r23, %r23, 4
	addi %r26, %r26, 4
	addi %r27, %r27, 1
	cmpwi %r4, 4
	blt  diff_coin_loop

	/* second loop: apply death penalties and calculate minimum/maximum coins */
	/*
	 * r3 - temp
	 * r4 - player index
	 * r5 - max lives
	 * r6 - max coins
	 * r7 - min coins
	 * r8 - temp 2
	 * r23 - present pointer
	 * r25 - results screen object
	 * r26 - resultsData pointer plus 4*index
	 * r27 - diff_coins pointer plus 4*index
	 */
	li   %r4, 0
	li   %r6, 0
	li   %r7, 999 /* a reasonably large number for the initial minimum */
	subi %r23, %r23, 16 /* reset to the beginning of the present list */
	mr   %r26, %r25
	mr   %r27, %r0
penalty_loop:
	lwz  %r3,  0(%r23)       /* check if the player we're looking at is present */
	cmpwi %r3, 0
	beq  penalty_loop_end    /* if r3 == 0, skip to the end of the loop */

	lwz  %r3, 0(%r27)  /* get coin count for this player */
	lwz  %r8, 0x08(%r26) /* get lives for this player */
	sub  %r8, %r5, %r8   /* get death penalty count = max lives - player lives */
	mullw %r8, %r8, %r31 /* multiply by death penalty amount */
	add  %r3, %r3, %r8   /* add to coin count */

	stw  %r3, 0(%r27) /* put it back for the next loop */

	cmpw %r3, %r6
	ble no_update_max_coins

	mr   %r6, %r3
no_update_max_coins:
	cmpw %r3, %r7
	bge no_update_min_coins

	mr   %r7, %r3
no_update_min_coins:
penalty_loop_end:
	/* increment everything */
	addi %r4,  %r4,  1
	addi %r23, %r23, 4
	addi %r26, %r26, 4
	addi %r27, %r27, 4
	cmpwi %r4, 4
	blt  penalty_loop

	/* third and final loop: calculate final score, apply final score, remove star coins */
	/*
	 * r3 - temp
	 * r4 - player index
	 * r5 - temp 2 (max lives not used anymore)
	 * r6 - maximum coins
	 * r7 - minimum coins
	 * r23 - present pointer
	 * r25 - results screen object
	 * r26 - resultsData pointer plus 4*index
	 * r27 - diff_coins pointer plus 4*index
	 */
	li   %r4,  0
	subi %r23, %r23, 16 /* move back to the beginning */
	mr   %r26, %r25
	mr   %r27, %r0

	stw  %r4,  0x58(%r26)    /* clear star coins */
final_score_loop:
	lwz  %r3,  0(%r23)       /* check if the player we're looking at is present */
	cmpwi %r3, 0
	beq  final_score_loop_end  /* if r3 == 0, skip to the end of the loop */

	/* get final score = (max coins - diff coins) + min coins */
	lwz  %r3,  0(%r27)  /* get diff coins */
	sub  %r3,  %r6, %r3 /* max - diff */
	add  %r3,  %r3, %r7 /* (max - diff) + min */

	/* lwz  %r6,  0x28(%r26) */
	/* sub  %r3,  %r3, %r6 */
	
	stw  %r3,  0x28(%r26) /* update base coins */
	li   %r3,  0
	stw  %r3,  0x48(%r26)

final_score_loop_end:
	/* increment everything */
	addi %r4,  %r4,  1
	addi %r23, %r23, 4
	addi %r26, %r26, 4
	addi %r27, %r27, 4
	cmpwi %r4, 4
	blt  final_score_loop

	/* done! cleanup and pretend nothing happened */
	lwz  %r3,  0x04(%r1)
	lwz  %r4,  0x08(%r1)
	lwz  %r5,  0x0c(%r1)
	lwz  %r23, 0x10(%r1)
	lwz  %r25, 0x14(%r1)
	lwz  %r26, 0x18(%r1)
	lwz  %r27, 0x1c(%r1)
	lwz  %r28, 0x20(%r1)
	lwz  %r30, 0x24(%r1)
	lwz  %r31, 0x28(%r1)
	lwz  %r0,  0x30(%r1)
	li   %r29, 1
	mtlr %r0
	addi %r1, %r1, 0x2c
	blr
diff_coins:
	.zero 16

	.globl patch_init_lives
patch_init_lives:
	/* called by the REL prolog */
	stwu %r1, -0xc(%r1)
	stw  %r3, 0x4(%r1)
	stw  %r4, 0x8(%r1)

	/* load our target address, 800e18dc */
	lis  %r3, 0x800e
	addi %r3, %r3, 0x18dc

	/* load our instruction data 38 60 00 63 */
	lis  %r4, 0x3860
	addi %r4, %r4, 99    /* number of lives */

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

