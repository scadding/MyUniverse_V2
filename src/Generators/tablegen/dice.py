from pyparsing import *

def convertNums(s):
    try:
        return int(s[0])
    except ValueError:
        return float(s[0])

LPAR,RPAR,POINT,COMMA = map(Suppress,"().,")
fnumber = Combine(Word(nums) + Optional("." + Optional(Word(nums))))
fnumber.setParseAction( convertNums )

fn = oneOf("minRoll maxRoll takeLowest takeHighest setMinimum")
dice = Combine(Optional(fnumber,default=1) + CaselessLiteral("d") + Word(nums))
args = Group(delimitedList(fnumber))
diceExpr = Group( dice + OneOrMore( Group(POINT + fn + LPAR + args + RPAR) ) )

atom = diceExpr | dice | fnumber
signop = oneOf('+ -')
multop = oneOf('* /')
plusop = oneOf('+ -')
fnop = Group(POINT + fn + LPAR + args + RPAR) 

expr = infixNotation( atom,
    [(signop, 1, opAssoc.RIGHT),
     (multop, 2, opAssoc.LEFT),
     (plusop, 2, opAssoc.LEFT),]
    )

def dice(s):
    results =  expr.parseString(s.decode())
    return evalExpr(results)

from random import randint
def roll(dieStr):
    count,sides = map(int,dieStr.split("d"))
    ret = [ randint(1,sides) for _ in range(count) ]
    #print "Rolling", dieStr, "->", ret  # debugging statement, comment out to disable
    return ret

def evalAtom(a):
    if isinstance(a, ParseResults):
        return evalExpr(a)
    if isinstance(a, (int,float)):
        return a
    if isinstance(a, str):
        return sum(roll(a))

binops = {
    '+' : (lambda a,b : a+b),
    '-' : (lambda a,b : a-b),
    '*' : (lambda a,b : a*b),
    }
def evalExpr(a):
    if isinstance(a,ParseResults) and \
        len(a)>1 and \
        isinstance(a[1],ParseResults):
        return evalDiceExpr(a)
        
    accum = evalAtom(a[0])
    for op,elem in zip(a[1::2],a[2::2]):
        accum = binops[op](accum,evalAtom(elem))
    return accum

sortedRoll = lambda dstr,revflag=False : sorted(roll(dstr),reverse=revflag)
takeLowest = lambda d,n : isinstance(d,str) and sortedRoll(d)[:n] or sorted(d)[:n]
takeHighest = lambda d,n : isinstance(d,str) and sortedRoll(d,revflag=True)[:n] or sorted(d,reverse=True)[:n]
minRoll = lambda d,n : sorted([ sortedRoll(d) for _ in range(n)])[0]
maxRoll = lambda d,n : sorted([ sortedRoll(d) for _ in range(n)],reverse=True)[0]
def setMinimum(d, n):
    #print d, n
    r = roll(d)
    #print r
    while r[0] < n:
        r = roll(d)
    return r
    
fns = {
    'takeLowest' : takeLowest,
    'takeHighest' : takeHighest,
    'minRoll' : minRoll,
    'maxRoll' : maxRoll,
    'setMinimum' : setMinimum,
    }
def evalDiceExpr(a):
    dice = a[0]
    for mod in a[1:]:
        dice = fns[mod[0]](dice, mod[1][0])
    return sum(dice)

'''
Method III: Roll 3d6 six times and jot down the total for each roll. Assign the scores
to your character's six abilities however you want. This gives you the chance to custom-
tailor your character, although you are not guaranteed high scores.
'''

'''
Method I: Roll three six-sided dice (3d6); the total shown on the dice is your
character's Strength ability score. Repeat this for Dexterity, Constitution, Intelligence,
Wisdom, and Chrisma, in that order. This method gives a range of scores from 3 to 18,
with most results in the 9 to 12 range. Only a few characters have high scores (15 and
above), so you should treasure these characters.
Alternative Dice-Rolling Methods
Method I creates characters whose ability scores are usually between 9 and 12. If you
would rather play a character of truly heroic proportions, ask your DM if he allows
players to use optional methods for rolling up characters. These optional methods are
designed to produce above-average characters.
'''

def method_I():
    result = list()
    for i in range(6):
        result.append(evalExpr(expr.parseString('3d6')))
    return result

'''
Method II: Roll 3d6 twice, noting the total of each roll. Use whichever result you
prefer for your character's Strength score. Repeat this for Dexterity, Constitution,
Intelligence, Wisdom, and Charisma. This allows you to pick the best score from each
pair, generally ensuring that your character does not have any really low ability scores
(but low ability scores are not all that bad any way!).
'''

def method_II():
    result = list()
    for i in range(6):
        r1 = evalExpr(expr.parseString('3d6'))
        r2 = evalExpr(expr.parseString('3d6'))
        result.append(max(r1, r2))
    return result

'''
Method IV: Roll 3d6 twelve times and jot down all twelve totals. Choose six of these
rolls (generally the six best rolls) and assign them to your character's abilities however
you want. This combines the best of methods II and III, but takes somewhat longer.
As an example, Joan rolls 3d6 twelve times and gets results of 12, 5, 6, 8, 10, 15, 9, 12,
6, 11, 10, and 7. She chooses the six best rolls (15, 12, 12, 11, 10, and 10) and then
assigns them to her character's abilities so as to create the strengths and weaknesses that
she wants her character to have (see the ability descriptions following this section forexplanations of the abilities).
'''

def highest_n(l, n):
    x = []
    x.extend(l)
    x.sort(reverse=True)
    a = x[:n]
    res = []
    for i in a:
        res.append(l.index(i))
    res.sort()
    r = list()
    for i in res:
        r.append(l[i])
    return r

def method_IV():
    result = list()
    for i in range(12):
        result.append(evalExpr(expr.parseString('3d6')))
    h = highest_n(result, 6)
    return h

'''
Method V: Roll four six-sided dice (4d6). Discard the lowest die and total the
remaining three. Repeat this five more times, then assign the six numbers to the
character's abilities however you want. This is a fast method that gives you a good
character, but you can still get low scores (after all, you could roll 1s on all four dice!).
Method VI: This method can be used if you want to create a specific type of character.
It does not guarantee that you will get the character you want, but it will improve your
chances.
'''

def method_V():
    result = list()
    for i in range(6):
        result.append(evalExpr(expr.parseString('4d6.takeHighest(3)')))
    return result

'''
Method VI: Each ability starts with a score of 8. Then roll seven dice. These dice can be added to
your character's abilities as you wish. All the points on a die must be added to the same
ability score. For example, if a 6 is rolled on one die, all 6 points must be assigned to one
ability. You can add as many dice as you want to any ability, but no ability score can
exceed 18 points. If you cannot make an 18 by exact count on the dice, you cannot have
an 18 score.
'''

def method_VI():
    highest = True
    average = False
    result = list()
    v = list()
    for i in range(7):
        v.append(evalExpr(expr.parseString('d6')))
    v.sort(reverse=True)
    for i in range(6):
        result.append(8)
    while len(v):
        success = False
        for i in range(6):
            # add values while value <= 18
            for j in range(len(v)):
                if v[j] + result[i] <= 18:
                    result[i] = result[i] + v[j]
                    v.remove(v[j])
                    success = True
                    break
            if highest and success:
                break
        if average and success:
            continue
    return result

def ability(method):
    print("Method =", method)
    if method == "I":
        result = method_I()
    elif method == "II":
        result = method_II()
    elif method == "IV":
        result = method_IV()
    elif method == "V":
        result = method_V()
    elif method == "VI":
        result = method_VI()
    print(result)

if __name__ == "__main__":
    test = '2d6*3-5.5+4d6.minRoll(2).takeHighest(3)'
    #~ test = 'D5+2d6*3-5.5+4d6.takeHighest(3)'
    #~ test = 'D5+2d6*3-5.5+4d6'
    results = expr.parseString(test)

    print(results)
    print(evalExpr(results))

    ability('VI')
