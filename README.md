# NSMBWii Zero Coin Battle Mod

Modifies coin battle mode in New Super Mario Bros. Wii so that the player with the least coins wins!

## Scoring

To improve game balance, a 10-coin penalty has been added per death (specifically, max lives minus player lives)
to offset the number of coins that are missed by sitting in a bubble. This penalty can be adjusted by changing
penalty\_value in `main.s` and rebuilding the patch.

Additionally, a target coin count (`target_coins`) can be set, which scores players based on how close their
coin count is to the target. If the target is too low (everyone's score is above it), the gameplay will be
nearly identical to normal zero-coin battle; but if it is too high, the gameplay effectively becomes regular
coin battle. A target somewhere between 50 and 100 coins is reasonable for most levels.

## Usage

You will need:
- an ISO file for the US version of New Super Mario Bros. Wii
   - Get this by ripping the disc using a soft-modded Wii console, see
     [https://dolphin-emu.org/docs/guides/ripping-games/](https://dolphin-emu.org/docs/guides/ripping-games/)
- Wiimm's ISO tools ([https://wit.wiimm.de/wit/](https://wit.wiimm.de/wit/))
- Python 3.7 or higher

Run `patchgame.py --iso <path to your ISO file> --output <output ISO/WBFS file>`
* If WIT cannot be found, specify where it is using the `--wit-path` option.

### Advanced usage

To reassemble the patch binary, you need devkitPPC ([https://devkitpro.org/wiki/Getting\_Started](https://devkitpro.org/wiki/Getting_Started))

Run `patchgame.py` as above, but with the `--assemble` option to run the assembly.
* If the devkitPPC binaries can't be found, specify the path with `--dkp-path`

## Technical info

NSMBWii's code is split into `main.dol` (the main executable) and several "relocatable" `.rel` files. The `.rel`
files are all loaded to fixed addresses while the wrist strap screen is displayed, so they are only used to reduce
the game's initial load time (as far as I can tell).

`main.dol` mostly contains the Revolution OS and game engine code. Most of the actual game code is contained in
`d_basesNP.rel.LZ`. This 'LZ' format is an enhanced version of Yaz0 compression, usually used in DS and GBA games.
(This game was most likely ported from the original DS version). The game will load uncompressed `rel` files in
place of compressed ones, which means that we don't need to worry about re-compressing our patched `rel` file.

`rel` files are organized in a similar fashion to ELF files, with `.text`/`.data`/`.bss`/etc. sections and
relocation tables. Since the section table has many empty entries, the patcher script can add code to one of these
empty sections. It then applies appropriate jump instructions within the original code.

For simplicity, the patcher only modifies `d_basesNP.rel`. Since the code layout in memory is fixed, additional
patches to `main.dol` and other files can be done at runtime by writing over the appropriate instruction and then
flushing the instruction cache at that address. 

-- More info coming soon, assuming I don't forget --

## License

This project is licensed under the MIT license. See the LICENSE file for details.
