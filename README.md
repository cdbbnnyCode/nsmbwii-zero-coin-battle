# NSMBWii Zero Coin Battle Mod

Modifies coin battle mode in New Super Mario Bros. Wii so that the player with the LEAST coins wins!

## Scoring

The mod adjusts the coin values shown on the results screen to reflect the player's "score" rather than
how many coins they actually got.

(more info soon)

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

## License

This project is licensed under the MIT license. See the LICENSE file for details.
