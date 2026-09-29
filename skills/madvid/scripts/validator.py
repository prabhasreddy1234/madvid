#!/usr/bin/env python3

from madvid.validation import validate_duration, validate_orientation, validate_style

if __name__ == "__main__":
    print(validate_duration(20))
    print(validate_orientation('landscape'))
    print(validate_style('minimal'))
