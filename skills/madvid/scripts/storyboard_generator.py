#!/usr/bin/env python3

from madvid.storyboard_generator import generate_storyboard

if __name__ == "__main__":
    for scene in generate_storyboard('Demo Product', 'Productivity', ['Track tasks', 'See results', 'Move faster'], 20):
        print(scene)
