import numpy as np

RANKS = '23456789TJQKA'
SUITS = 'cdhs'

class Card:
    def __init__(self, rank, suit):
        if rank not in RANKS or suit not in SUITS:
            raise TypeError("Invalid card")
        
        self.rank = rank
        self.suit = suit
    
    def __repr__(self):
        return self.rank+self.suit
    
    def __lt__(self, other):
        return self.__hash__() < other.__hash__()
    
    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit
    
    def __hash__(self):
        return RANKS.index(self.rank) * 4 + SUITS.index(self.suit)
    
DECK = [Card(R,S) for R in RANKS for S in SUITS] #Creates 52 card deck
    
class Grouping:
    # Valid labels like 'AA', 'AKo', '76s' describe hands in 13x13 preflop hand groups
    # Labels are 2-A (capital letters), and 'o' or 's' to describe the suits
    # Pocket pairs don't need 'o' or 's'
    # Purpose of class is to allow natural range selection, and to set up suit isomorphisms
    def __init__(self, label):
        if label[0] not in RANKS or label[1] not in RANKS:
            raise BaseException("Invalid rank label")
        if len(label) == 3 and label[-1] not in 'so' or len(label) == 2 and label[0] != label[1]:
            raise BaseException("Choose 'o' or 's' for labeling non paired hole cards")
        if len(label) < 2 or len(label) > 3:
            raise BaseException("Invalid label")
        if RANKS.index(label[0]) < RANKS.index(label[1]):
            label = label[1]+label[0]+label[2]
        
        self.label = label
        self.getCombos()
        self.group = None
    
    def getCombos(self):
        # Defines all preflop combos for a label
        # Ex: grouping 76s combos = [7c6c, 7d6d, 7h6h, 7s6s]
        if len(self.label) == 2:
            i = RANKS.index(self.label[0])*4
            self.combos = [(DECK[i+j],DECK[i+k]) for j in range(3) for k in range(j, 4) if j!=k]
        
        elif 's' in self.label:
            i, j = RANKS.index(self.label[0])*4, RANKS.index(self.label[1])*4
            self.combos = [(DECK[i+k],DECK[j+k]) for k in range(4)]
            
        elif 'o' in self.label:
            i, j = RANKS.index(self.label[0])*4, RANKS.index(self.label[1])*4
            self.combos = [(DECK[i+k], DECK[j+l]) for k in range(4) for l in range(4) if k != l]
    
    def applyiso(self, notiso):
        # Groups together strategically equivalent combos
        if not notiso:
            self.group = [self.combos]
        else:
            self.group = []
            iso = set(SUITS) - set(notiso)
            if 's' in self.label:
                self.group.append([c for c in self.combos if c[0].suit in iso])
                    
                for i in range(len(notiso)):
                    self.group.append([c for c in self.combos if c[0].suit in notiso[i]])
                    
            elif len(iso) <= 1:
                self.group = [[c] for c in self.combos]
            
                
            else:
                temp = [c for c in self.combos if c[0].suit in iso and c[1].suit in iso]
                self.group.append(temp)
                for i in range(len(notiso)):
                    temp = [c for c in self.combos if c[0].suit in iso and c[1].suit in notiso[i] or c[1].suit in iso and c[0].suit in notiso[i]]
                    if temp:
                        self.group.append(temp)
                temp = [c for c in self.combos if c[0].suit in notiso[-1] and c[1].suit in notiso[0] or c[0].suit in notiso[0] and c[1].suit in notiso[-1]]
                if temp:
                    self.group.append(temp)
            
    def __repr__(self):
        return self.label
    
    def __eq__(self, other):
        return self.label == other.label
    

def createNLHands(ordering=None):
    #Creates ordered list of all 169 starting hand groupings based on some labeled ordering
    NLhands = []
    if ordering:
        for label in ordering:
            NLhands.append(Grouping(label))
    else:
        for r in RANKS:
            for s in RANKS:
                if r == s:
                    NLhands.append(Grouping(r+s))
                elif RANKS.index(r) > RANKS.index(s):
                    NLhands.append(Grouping(r+s+'s'))
                    NLhands.append(Grouping(r+s+'o'))
    
    return NLhands

nlhands = createNLHands(lowres) #Creates starting hand groups

def applyiso(board):
    #Groups together strategically equivalent combos for all starting hands
    sboard = [c.suit for c in board]
    notiso = [s for s in SUITS if sboard.count(s) > 2]
    if not notiso:
        notiso = ''
    else:
        notiso = notiso[0]
    
    for grouping in nlhands:
        grouping.applyiso(notiso)

    
def toppercent(percent):
    return nlhands[:int(percent*1.69)]
    
    
def flush(cards):
    suits = [c.suit for c in cards]
    if max([suits.count(s) for s in SUITS]) > 4:
        fs = [s for s in SUITS if suits.count(s) > 4]
        return sorted([c for c in cards if c.suit == fs[0]], reverse=True)[:5]
    else:
        return False
        
def straight(cards):
    ranks = sorted([RANKS.index(c.rank) for c in cards])
    if 12 in ranks:
        ranks.insert(0, -1)
    c=0
    for i in range(len(ranks)-1):
        if ranks[i]+1 >= ranks[i+1]:
            if ranks[i]+1 == ranks[i+1]:
                c += 1
            if i == len(ranks)-1 and c > 3:
                return RANKS[ranks[i]]
        elif c > 3:
            return RANKS[ranks[i]]
        
        elif len(ranks)-1 - i < 4:
            return False
        else:
            c=0

    
def Rank(hand, board):
    # Classifies 7 card hand
    if len(hand) != 2 or len(board) != 5:
        raise BaseException("Invalid hand or board")
    
    if len(set(hand+board))!= 7:
        return None
    cards = sorted(hand+board, reverse=True)
    
    if flush(cards):
        if straight(flush(cards)):
            return 8, straight(flush(cards))
        else:
            return 5, flush(cards)
    
    if straight(cards):
        return 4, straight(cards)
    
    counts = [c.rank for c in cards]
    counts = [counts.count(r) for r in RANKS]
    cards = [c.rank for c in cards]
    
    if max(counts) == 1:
        return 0, cards[:5]
    if max(counts) == 2 and counts.count(2) == 1:
        cards = [c for c in cards if c != RANKS[counts.index(2)]]
        cards.insert(0,RANKS[counts.index(2)])
        return 1, cards[:4]
    if max(counts) == 2 and counts.count(2) > 1:
        pairs = sorted([RANKS.index(r) for r in RANKS if counts[RANKS.index(r)] == 2], reverse=True)[:2]
        pairs = [RANKS[r] for r in pairs]
        high = sorted([RANKS.index(c) for c in cards if c not in pairs])[-1]
        pairs.append(RANKS[high])
        return 2, pairs
    if max(counts) == 3 and counts.count(3) == 1 and counts.count(2) == 0:
        cards = [c for c in cards if c != RANKS[counts.index(3)]]
        cards.insert(0, RANKS[counts.index(3)])
        return 3, cards[:3]
    if max(counts) == 3 and (counts.count(2) > 0 or counts.count(3) > 1):
        trips = sorted([RANKS.index(r) for r in RANKS if counts[RANKS.index(r)] == 3], reverse=True)
        pairs = sorted([RANKS.index(r) for r in RANKS if counts[RANKS.index(r)] == 2], reverse=True)
        trips = [RANKS[r] for r in trips]
        if pairs:
            trips.append(RANKS[pairs[0]])
        return 6, trips[:2]
    if max(counts) == 4:
        quads = [RANKS[counts.index(4)]]
        high = sorted([RANKS.index(c) for c in cards if c not in quads])[-1]
        quads.append(RANKS[high])
        return 7, quads
    
    
def rankvalue(rank1):
    # Makes 7 card classification orderable
    if rank1 == None:
        return None
    temp = rank1[0]
    if rank1[0] == 5:
        rank1 = [RANKS.index(r.rank) for r in rank1[1]]
    else:
        rank1 = [RANKS.index(r) for r in rank1[1]]
    
    rank1.insert(0, temp)
    return tuple(rank1)
    
def randBoard():
    return tuple(np.random.choice(DECK, 5, replace=False))


def makeRange(percent, board):
    # Returns range of top % of hands
    applyiso(board)
    hands = toppercent(percent)
    groups = []
    for hand in hands:
        for group in hand.group:
            g = []
            for combo in group:
                #Makes sure specific combos in grouping do not overlap with board
                if combo[0] not in board and combo[1] not in board:
                    g.append(combo)
            if g:
                groups.append(g)
    return groups
    
    
