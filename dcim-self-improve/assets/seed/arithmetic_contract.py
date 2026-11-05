"""Check proposed7bit signed/unsigned reduction topology independently.

For8 terms, complementing bit3 of each4bit product adds a constant64 relative
to signed arithmetic. Therefore a single finalbit6 XOR removes that offset.
All8 terms must undergo the transform, including inactive zero products.
This contract is topology planning, not transistor or layout qualification.
"""
import json
import random


def fa(a,b,c):
    return a^b^c,(a&b)|(a&c)|(b&c)


def add(a,b,width):
    carry=0
    out=0
    for i in range(width):
        s,carry=fa((a>>i)&1,(b>>i)&1,carry)
        out |= s<<i
    return out|(carry<<width)


def tree(words,active,sign):
    terms=[(v if (active>>i)&1 else 0)^(8 if sign else 0)
           for i,v in enumerate(words)]
    for width in (4,5,6):
        terms=[add(a,b,width) for a,b in zip(terms[::2],terms[1::2])]
    return terms[0]^(64 if sign else 0)


def main():
    rng=random.Random(12)
    count=0
    for words in ([0]*8,[15]*8,[8]*8,[7]*8,list(range(8)),list(range(8,16))):
        for active in range(256):
            for sign in (0,1):
                expected=sum((v-16 if sign and v&8 else v)
                             for i,v in enumerate(words) if (active>>i)&1)&127
                assert tree(words,active,sign)==expected
                count+=1
    for _ in range(4096):
        words=[rng.randrange(16) for _ in range(8)]
        active=rng.randrange(256)
        for sign in (0,1):
            expected=sum((v-16 if sign and v&8 else v)
                         for i,v in enumerate(words) if (active>>i)&1)&127
            assert tree(words,active,sign)==expected
            count+=1
    result=dict(samples=count,passed=True,per_channel=True,
                topology="4x4bit+2x5bit+1x6bit wideningadders;8productMSB_XOR and1finalMSB_XOR",
                required_full_adders_per_output=32,
                electrical_qualified=False,layout_qualified=False)
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
