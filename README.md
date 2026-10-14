# LIS4062 Homework 3: Enigma Machine and GF(2^3)

Source code for the Enigma machine and finite-field parts of Homework No. 3 of LIS4062 Information Security (Universidad de las Américas Puebla, Autumn 2026).
The KE-DES implementation of the same homework is in a separate repository: https://github.com/AdalCastilla/KEDES

Authors: Adalberto Castilla Alcántara, Gartzen Aldecoa Barroso, Rishabh Verma.

Both programs are written from scratch in Python 3 and use only the standard library.

## Files

| File | Contents |
|---|---|
| `enigma.py` | Enigma I simulator (rotors I to V, reflector B, ring settings, plugboard and double stepping) and a Bombe-style known-plaintext attack that recovers the rotor order, start position and plugboard from a 23-letter crib. |
| `gf8.py` | Addition and multiplication tables of GF(2^3) with the irreducible polynomial m(x) = x^3 + x + 1. |

## Running

```bash
python3 enigma.py
python3 gf8.py
```

`enigma.py` first checks the simulator against the published test vectors (`AAAAA` encrypts to `BDZGO` with rotors I-II-III, rings 01-01-01 and start AAA). It then encrypts and decrypts a test message and runs the attack. The attack tests all 1,054,560 rotor orders and positions and uses every CPU core, so it takes about 20 seconds on a laptop. It assumes the ring settings are known.

`gf8.py` prints both tables, the inverse of every element and the powers of the generator x, followed by the LaTeX code of the tables.

## License

MIT, see `LICENSE`.
