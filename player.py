import pokerlogic

class Player:
    def __init__(self, hands):
        #'hands' are a list of strategically equivalent combos as defined in the grouping class
        #Ex: [(Ad, Ah), (Ad, As), (Ah, As)]
        self.hands = hands
        #Each combo is assumed to be equally weighted, so 'hands' have weights proportional
        #to their length
        self.initweights = np.array([len(h)/len(self.hands) for h in self.hands])
        self.initweights /= np.sum(self.initweights)
    

def CreateRankOrder(p1, p2, board):
    #This function generates a mapping of showdown equity for 'hand' -> villain range
    #for all 'hands' in both players ranges
    #This only needs to be generated once when building the tree, and allows for fast calculation
    #when stored as numpy objects
    p1values = [rankvalue(Rank(h[0], board)) for h in p1.hands]
    p2values = [rankvalue(Rank(h[0], board)) for h in p2.hands]
    # 'rou' stands for 'RankOrderUnits' and 'row' stands for 'RankOrderWeights'
    # 'RankOrderUnits' keep track of removal for each hand match-up
    # 'RankOrderWeights' are the equity for each hand match-up multiplied by 'RankOrderUnits'.
    p1rou = []
    p1row = []
    p2rou = []
    p2row = []
    for i in range(len(p1.hands)):
        temprou = []
        temprow = []
        for j in range(len(p2.hands)):
            removal = 0
            for k in range(len(p1.hands[i])):
                rem = 0
                for hand in p2.hands[j]:
                    if p1.hands[i][k][0] in hand or p1.hands[i][k][1] in hand:
                        rem += 1
                rem = 1-rem/len(p2.hands[j])
                removal += rem
            
            removal/=len(p1.hands[i])
            temprou.append(removal)
            
            if p1values[i] > p2values[j]:
                temprow.append(removal)
            elif p1values[i] == p2values[j]:
                temprow.append(.5*removal)
            else:
                temprow.append(0)
                
        p1rou.append(temprou)
        p1row.append(temprow)

    for i in range(len(p2.hands)):
        temprou = []
        temprow = []
        for j in range(len(p1.hands)):
            removal = 0
            for k in range(len(p2.hands[i])):
                rem = 0
                for hand in p1.hands[j]:
                    if p2.hands[i][k][0] in hand or p2.hands[i][k][1] in hand:
                        rem += 1
                rem = 1-rem/len(p1.hands[j])
                removal += rem
                
            removal/=len(p2.hands[i])
            temprou.append(removal)
            
            if p2values[i] > p1values[j]:
                temprow.append(removal)
            elif p2values[i] == p1values[j]:
                temprow.append(.5*removal)
            else:
                temprow.append(0)
                
        p2rou.append(temprou)
        p2row.append(temprow)
        
    return np.array(p1rou).astype(float), np.array(p2rou).astype(float), np.array(p1row).astype(float), np.array(p2row).astype(float)