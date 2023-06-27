#!/usr/bin/env python3

import subprocess
import sys
import os
import argparse
import shutil
import shlex
import pathlib

import lzdec
import patcher

def run(*cmd, workdir='.', stdout=None):
    print("> " + shlex.join(cmd))
    subprocess.run(cmd, cwd=workdir, stdout=stdout, check=True)

def get_program(f, path):
    if path is None: return f
    else: return os.path.join(path, f)

def assemble(asm_file, devkitppc_path=None):
    base, ext = os.path.splitext(asm_file)
    wd = 'asm'
    run(get_program('powerpc-eabi-as', devkitppc_path), 
        '-mbroadway', '-a', asm_file, '-o', base + '.o', workdir=wd)

    run(get_program('powerpc-eabi-ld', devkitppc_path),
        '-T', 'ldscript.ld', base + '.o', '-o', base + '.elf', workdir=wd)

    run(get_program('powerpc-eabi-objcopy', devkitppc_path),
        '--dump-section', '.text=%s.bin' % base, base + '.elf', workdir=wd)

    with open(os.path.join(wd, base + '.syms'), 'w') as f:
        run(get_program('powerpc-eabi-readelf', devkitppc_path),
            '--syms', base+'.elf', workdir=wd, stdout=f)

def main():
    # arguments for advanced use:
    #   -a | --assemble        : assemble (needs devkitPPC)
    #   -d | --dkp-path <path> : look for devkitPPC binaries in this location
    #   -w | --wit-path <path> : look fof WIT in this location
    #   -i | --iso      <file> : path to the input ISO
    #   -o | --output   <file> : output ISO/WBFS

    parser = argparse.ArgumentParser()

    parser.add_argument('-a', '--assemble', action='store_true', dest='assemble',
                        help='Assemble the patch binary. Requires devkitPPC')
    parser.add_argument('-d', '--dkp-path', dest='dkp_path', metavar='path',
                        help='Path to devkitPPC binaries for the --assemble option')
    parser.add_argument('-w', '--wit-path', dest='wit_path', metavar='path',
                        help='Path to WIT binaries')
    parser.add_argument('-i', '--iso', dest='iso_path', metavar='path',
                        help='Path to the input (clean) ISO file')
    parser.add_argument('-o', '--output', dest='output_path', metavar='path', required=True,
                        help='Path to the output ISO/WBFS file')

    args = parser.parse_args()

    if args.assemble:
        assemble('main.s', args.dkp_path)
    
    pathlib.Path('game').mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists('game/data'):
        # extract the game if it isn't already
        print()
        print("Extracting game files...")

        run(get_program('wit', args.wit_path),
            '--psel', 'DATA', 'extract', os.path.abspath(args.iso_path), 'data', workdir='game')

    # decompress the REL file if necessary
    decomp_rel = 'd_basesNP.rel.orig'

    if not os.path.exists(decomp_rel):
        lzfile = 'game/data/files/rels/d_basesNP.rel.LZ'
        rename = True
        if not os.path.exists(lzfile):
            # use the renamed file
            lzfile += '_'
            rename = False

        with open(lzfile, 'rb') as f:
            in_data = f.read()
            data = lzdec.lzdec(in_data)
            with open(decomp_rel, 'wb') as of:
                of.write(data)
            # explicitly clear out these huge data blocks
            del in_data
            del data

        if rename:
            # rename the LZ file so that the game doesn't pick it up
            os.rename(lzfile, lzfile + '_') 

    # throw the output directly into the game files
    # The game's read function will transparently open this file if the LZ file doesn't exist
    out_file = "game/data/files/rels/d_basesNP.rel"

    patch_spec = {
        "rel": "d_basesNP.rel.orig",
        "output": "game/data/files/d_basesNP.rel",
        "sections": [
            {
                # define the section for our patch data
                # this goes into an empty section in the REL
                "ref": "main",
                "file": "asm/main.bin",
                "symtab": "asm/main.syms"
            }
        ],

        "patches": [
            # patches into the REL file itself
            {
                # patch the results data calculation
                "type": "branch_section",
                "section": 1,
                "addr": 0x37d68,  # where to put the branch
                "target": "main", # function to jump to
                "target_section": "main"
            },
            {
                # patch the prolog to add a init lives patcher
                # The init lives calculation is in main.dol (which we don't have a patcher for)
                # so we have a runtime patcher
                "type": "branch_section",
                "section": 1,
                "addr": 0x10c,
                "target": "patch_init_lives",
                "target_section": "main"
            }
        ]
    }

    # Run the patcher
    patcher.main(patch_spec)

    # re-pack the game
    print()
    print("Re-packing game...")

    run(get_program('wit', args.wit_path),
        'copy', 'data/', os.path.abspath(args.output_path), workdir='game')
    
    print()
    print("Done!")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print("Error: process returned %d" % e.returncode)
