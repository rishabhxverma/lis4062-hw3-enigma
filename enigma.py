#Enigma I (Wehrmacht/Luftwaffe) simulator and crib-based attack
#Written from scratch, no cryptographic libraries are used
import time
from itertools import permutations
from multiprocessing import Pool

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#Rotor wirings and turnover notches of the Enigma I
ROTORS = {
    "I":   ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"),
    "II":  ("AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"),
    "III": ("BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
    "IV":  ("ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"),
    "V":   ("VZBRGITYUPSDNHLXAWMJQOFECK", "Z"),
}

#Reflector B (Umkehrwalze B)
REFLECTOR_B = "YRUHQSLDPXNGOKMIEBFZCWVJAT"


def to_num(letter):
    return ord(letter) - ord("A")


def to_letter(num):
    return ALPHABET[num % 26]


#Plugboard: list of pairs such as ["AB", "CD"] -> substitution table
def build_plugboard(pairs):
    table = list(range(26))

    for pair in pairs:
        a, b = to_num(pair[0]), to_num(pair[1])

        if table[a] != a or table[b] != b:
            raise ValueError("A letter can only be plugged once")

        table[a] = b
        table[b] = a

    return table


#Signal through one rotor, right to left
def rotor_forward(c, wiring, position, ring):
    shift = position - ring
    return (to_num(wiring[(c + shift) % 26]) - shift) % 26


#Signal through one rotor, left to right (inverse wiring)
def rotor_backward(c, wiring, position, ring):
    shift = position - ring
    return (wiring.index(to_letter(c + shift)) - shift) % 26


#Rotor stepping, including the double step of the middle rotor
def step_positions(positions, notches):
    left, middle, right = positions

    if middle == notches[1]:
        left = (left + 1) % 26
        middle = (middle + 1) % 26
    elif right == notches[2]:
        middle = (middle + 1) % 26

    right = (right + 1) % 26

    return [left, middle, right]


#Enigma encryption. Decryption is the same function with the same key
def enigma(text, rotor_order, ring_settings, start_positions, plug_pairs, trace=False):
    wirings = [ROTORS[name][0] for name in rotor_order]
    notches = [to_num(ROTORS[name][1]) for name in rotor_order]
    rings = [r - 1 for r in ring_settings]
    positions = [to_num(p) for p in start_positions]
    plugboard = build_plugboard(plug_pairs)

    result = ""

    for letter in text:
        #The rotors move before the electrical contact is made
        positions = step_positions(positions, notches)

        path = [letter]

        #Plugboard
        c = plugboard[to_num(letter)]
        path.append(to_letter(c))

        #Right, middle and left rotor
        for i in (2, 1, 0):
            c = rotor_forward(c, wirings[i], positions[i], rings[i])
            path.append(to_letter(c))

        #Reflector
        c = to_num(REFLECTOR_B[c])
        path.append(to_letter(c))

        #Left, middle and right rotor
        for i in (0, 1, 2):
            c = rotor_backward(c, wirings[i], positions[i], rings[i])
            path.append(to_letter(c))

        #Plugboard
        c = plugboard[c]
        path.append(to_letter(c))

        if trace:
            window = "".join(to_letter(p) for p in positions)
            print(window, " -> ".join(path))

        result += to_letter(c)

    return result


#Number of daily keys of the Enigma I
def factorial(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def plugboard_settings(pairs):
    return factorial(26) // (factorial(26 - 2 * pairs) * factorial(pairs) * 2 ** pairs)


def key_space():
    rotor_orders = 5 * 4 * 3
    ring_settings = 26 ** 3
    positions = 26 ** 3
    plugs = plugboard_settings(10)

    return rotor_orders, ring_settings, positions, plugs


#Index of coincidence
def index_of_coincidence(text):
    n = len(text)
    counts = [text.count(letter) for letter in ALPHABET]
    return sum(f * (f - 1) for f in counts) / (n * (n - 1))


#A letter is never encrypted to itself, so the crib cannot be placed
#where one of its letters matches the ciphertext letter above it
def crib_positions(cipher, crib):
    valid = []

    for offset in range(len(cipher) - len(crib) + 1):
        segment = cipher[offset:offset + len(crib)]

        if all(a != b for a, b in zip(segment, crib)):
            valid.append(offset)

    return valid


#Lookup tables rotor -> position -> input letter (ring setting 01)
FORWARD = {}
BACKWARD = {}

for name, (wiring, notch) in ROTORS.items():
    FORWARD[name] = [
        [rotor_forward(c, wiring, p, 0) for c in range(26)] for p in range(26)
    ]
    BACKWARD[name] = [
        [rotor_backward(c, wiring, p, 0) for c in range(26)] for p in range(26)
    ]

REFLECTOR = [to_num(letter) for letter in REFLECTOR_B]


#Menu: for each letter, the crib positions where it appears and the letter
#it is linked to at that position
def build_menu(cipher_segment, crib):
    menu = [[] for _ in range(26)]

    for i, (p, c) in enumerate(zip(crib, cipher_segment)):
        menu[to_num(p)].append((i, to_num(c)))
        menu[to_num(c)].append((i, to_num(p)))

    return menu


#Test every rotor position of one rotor order against the menu.
#For each position the 26 plugboard partners of the central letter are
#assumed in turn and their consequences are followed through the menu.
#A hypothesis that never contradicts itself is a "stop"
def bombe_search(job):
    order, cipher_segment, crib = job

    menu = build_menu(cipher_segment, crib)
    central = max(range(26), key=lambda letter: len(menu[letter]))
    notches = [to_num(ROTORS[name][1]) for name in order]
    f_left, f_middle, f_right = (FORWARD[name] for name in order)
    b_left, b_middle, b_right = (BACKWARD[name] for name in order)
    length = len(crib)

    stops = []

    for start in range(26 ** 3):
        positions = [start // 676, (start // 26) % 26, start % 26]
        states = []

        for _ in range(length):
            positions = step_positions(positions, notches)
            states.append(positions)

        for guess in range(26):
            plug = [-1] * 26
            pending = [(central, guess)]
            consistent = True

            while pending and consistent:
                letter, partner = pending.pop()

                for a, b in ((letter, partner), (partner, letter)):
                    if plug[a] == -1:
                        plug[a] = b
                    elif plug[a] != b:
                        consistent = False
                        break
                    else:
                        continue

                    for i, other in menu[a]:
                        l, m, r = states[i]
                        x = f_left[l][f_middle[m][f_right[r][b]]]
                        x = REFLECTOR[x]
                        x = b_right[r][b_middle[m][b_left[l][x]]]

                        if plug[other] == -1:
                            pending.append((other, x))
                        elif plug[other] != x:
                            consistent = False
                            break

                    if not consistent:
                        break

            if consistent:
                stops.append((start, plug))

    return order, stops


def plug_to_pairs(plug):
    pairs = []

    for a in range(26):
        if plug[a] > a:
            pairs.append(to_letter(a) + to_letter(plug[a]))

    return pairs


#Complete the plugboard: letters not fixed by the crib are paired when
#the pair raises the index of coincidence of the decrypted message
def complete_plugboard(cipher, order, start, plug):
    pairs = plug_to_pairs(plug)
    free = [to_letter(a) for a in range(26) if plug[a] == -1]
    best = index_of_coincidence(enigma(cipher, order, [1, 1, 1], start, pairs))
    improved = True

    while improved and len(pairs) < 13:
        improved = False
        choice = None

        for i in range(len(free)):
            for j in range(i + 1, len(free)):
                trial = pairs + [free[i] + free[j]]
                score = index_of_coincidence(
                    enigma(cipher, order, [1, 1, 1], start, trial)
                )

                if score > best:
                    best = score
                    choice = (free[i], free[j])

        if choice:
            pairs.append(choice[0] + choice[1])
            free.remove(choice[0])
            free.remove(choice[1])
            improved = True

    return pairs, best


#Known-plaintext attack. The ring settings are assumed to be 01-01-01
def crib_attack(cipher, crib, offset):
    segment = cipher[offset:offset + len(crib)]
    orders = list(permutations(ROTORS.keys(), 3))
    jobs = [(order, segment, crib) for order in orders]

    with Pool() as pool:
        results = pool.map(bombe_search, jobs)

    candidates = []
    total_stops = 0

    for order, stops in results:
        total_stops += len(stops)

        for start, plug in stops:
            #The search started at the crib, step back to the message start
            window = start_before(order, start, offset)

            if window is None:
                continue

            text = enigma(cipher, order, [1, 1, 1], window, plug_to_pairs(plug))
            candidates.append((index_of_coincidence(text), order, window, plug))

    candidates.sort(key=lambda item: item[0], reverse=True)

    return total_stops, candidates


#Window setting "offset" letters before a given rotor state
def start_before(order, state, offset):
    if offset == 0:
        return "".join(to_letter(x) for x in (state // 676, (state // 26) % 26, state % 26))

    notches = [to_num(ROTORS[name][1]) for name in order]
    target = [state // 676, (state // 26) % 26, state % 26]

    for start in range(26 ** 3):
        positions = [start // 676, (start // 26) % 26, start % 26]

        for _ in range(offset):
            positions = step_positions(positions, notches)

        if positions == target:
            return "".join(to_letter(x) for x in (start // 676, (start // 26) % 26, start % 26))

    return None


if __name__ == "__main__":

    print("Verification with known test vectors")
    print("I-II-III, rings 01-01-01, AAA:",
          enigma("AAAAA", ["I", "II", "III"], [1, 1, 1], "AAA", []))
    print("I-II-III, rings 02-02-02, AAA:",
          enigma("AAAAA", ["I", "II", "III"], [2, 2, 2], "AAA", []))

    #Daily key used for the encryption and decryption test
    rotor_order = ["II", "IV", "V"]
    ring_settings = [2, 21, 12]
    start_positions = "BLA"
    plug_pairs = ["AV", "BS", "CG", "DL", "FU", "HZ", "IN", "KM", "OW", "RX"]

    plaintext = "INFORMATIONSECURITYHOMEWORKTHREE"

    print("\nSignal path of the first five letters")
    enigma(plaintext[:5], rotor_order, ring_settings, start_positions,
           plug_pairs, trace=True)

    print("\nEncryption")
    start_time = time.perf_counter_ns()
    cipher = enigma(plaintext, rotor_order, ring_settings, start_positions, plug_pairs)
    end_time = time.perf_counter_ns()
    print("Plaintext: ", plaintext)
    print("Ciphertext:", cipher)
    print(f"Time: {(end_time - start_time) / 1_000_000:.3f} milliseconds")

    print("\nDecryption")
    decrypted = enigma(cipher, rotor_order, ring_settings, start_positions, plug_pairs)
    print("Decrypted: ", decrypted)
    print("Recovered the plaintext:", decrypted == plaintext)
    print("Letters encrypted to themselves:",
          sum(a == b for a, b in zip(plaintext, cipher)))

    print("\nDouble step of the middle rotor (I-II-III, start ADU)")
    positions = [to_num(p) for p in "ADU"]
    notches = [to_num(ROTORS[name][1]) for name in ["I", "II", "III"]]
    sequence = ["ADU"]
    for _ in range(4):
        positions = step_positions(positions, notches)
        sequence.append("".join(to_letter(p) for p in positions))
    print(" -> ".join(sequence))

    print("\nKey space")
    orders, rings, starts, plugs = key_space()
    total = orders * rings * starts * plugs
    print("Rotor orders:", orders)
    print("Ring settings:", rings)
    print("Start positions:", starts)
    print("Plugboard settings (10 cables):", plugs)
    print("Total:", total, f"(about 2^{total.bit_length() - 1})")
    print("Without plugboard and ring settings:", orders * starts)

    print("\nKnown-plaintext attack")
    secret_order = ["IV", "I", "III"]
    secret_start = "KDP"
    secret_plugs = ["AM", "BY", "CH", "DR", "EL", "FX", "GO", "IZ", "KW", "PT"]

    message = ("WETTERVORHERSAGEBISKAYAXHEUTEABENDSTARKERWINDAUSNORDWEST"
               "XSEEGANGVIERXSICHTWEITEZEHNKILOMETERXREGENSCHAUERXLUFTDRUCK"
               "FALLENDXTEMPERATURZWOELFGRAD")
    crib = "WETTERVORHERSAGEBISKAYA"

    intercepted = enigma(message, secret_order, [1, 1, 1], secret_start, secret_plugs)
    print("Ciphertext:", intercepted)
    print("Length:", len(intercepted))
    print("Index of coincidence of the ciphertext:",
          round(index_of_coincidence(intercepted), 4))
    print("Crib:", crib)

    valid = crib_positions(intercepted, crib)
    total_offsets = len(intercepted) - len(crib) + 1
    print(f"Crib positions without a letter clash: {len(valid)} of {total_offsets}")
    print("Position 0 allowed:", 0 in valid)

    start_time = time.perf_counter()
    total_stops, candidates = crib_attack(intercepted, crib, 0)
    elapsed = time.perf_counter() - start_time

    print("Rotor settings tested:", 60 * 26 ** 3)
    print("Plugboard hypotheses tested:", 60 * 26 ** 3 * 26)
    print("Stops:", total_stops)
    print(f"Search time: {elapsed:.1f} seconds")

    print("\nBest five stops by index of coincidence")
    for score, order, window, plug in candidates[:5]:
        print(f"{score:.4f}", "-".join(order), window, " ".join(plug_to_pairs(plug)))

    score, order, window, plug = candidates[0]
    pairs, final_score = complete_plugboard(intercepted, order, window, plug)
    recovered = enigma(intercepted, order, [1, 1, 1], window, pairs)

    print("\nRecovered key")
    print("Rotor order:", "-".join(order))
    print("Start position:", window)
    print("Plug pairs from the crib:", " ".join(plug_to_pairs(plug)))
    print("Plug pairs after completion:", " ".join(sorted(pairs)))
    print("Index of coincidence:", round(final_score, 4))
    print("Recovered text:", recovered)
    print("Attack successful:", recovered == message)
