#Addition and multiplication tables for GF(2^3)
#Irreducible polynomial m(x) = x^3 + x + 1 -> 1011

M = 0b1011
N = 3


#Addition of two polynomials over GF(2) is a bitwise XOR
def gf_add(a, b):
    return a ^ b


#Shift-and-add multiplication followed by reduction modulo m(x)
def gf_mul(a, b):
    result = 0

    for i in range(N):
        if (b >> i) & 1:
            result ^= a << i

    #Reduce the terms of degree 4 and 3
    for degree in range(2 * N - 2, N - 1, -1):
        if (result >> degree) & 1:
            result ^= M << (degree - N)

    return result


def polynomial(a):
    terms = []

    if a & 4:
        terms.append("x^2")
    if a & 2:
        terms.append("x")
    if a & 1:
        terms.append("1")

    return " + ".join(terms) if terms else "0"


def print_table(title, symbol, operation):
    print(title)
    print(f" {symbol}  | " + " ".join(format(b, "03b") for b in range(8)))
    print("-" * 37)

    for a in range(8):
        row = " ".join(format(operation(a, b), "03b") for b in range(8))
        print(f"{format(a, '03b')} | {row}")

    print()


def latex_table(symbol, operation):
    lines = ["\\begin{tabular}{c|cccccccc}"]
    lines.append(f"${symbol}$ & " + " & ".join(format(b, "03b") for b in range(8)) + " \\\\ \\hline")

    for a in range(8):
        row = " & ".join(format(operation(a, b), "03b") for b in range(8))
        lines.append(f"{format(a, '03b')} & {row} \\\\")

    lines.append("\\end{tabular}")

    return "\n".join(lines)


if __name__ == "__main__":

    print_table("Addition in GF(2^3)", "+", gf_add)
    print_table("Multiplication in GF(2^3) modulo x^3 + x + 1", "x", gf_mul)

    print("Elements and inverses")
    for a in range(8):
        additive = next(b for b in range(8) if gf_add(a, b) == 0)
        multiplicative = next((b for b in range(8) if gf_mul(a, b) == 1), None)
        inverse = format(multiplicative, "03b") if multiplicative is not None else "---"
        print(format(a, "03b"), a, polynomial(a).ljust(12),
              format(additive, "03b"), inverse)

    print("\nPowers of the generator g = x (010)")
    power = 1
    for k in range(8):
        print(f"g^{k} = {format(power, '03b')} = {polynomial(power)}")
        power = gf_mul(power, 0b010)

    print("\nLaTeX")
    print(latex_table("+", gf_add))
    print()
    print(latex_table("\\times", gf_mul))
