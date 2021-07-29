import player

    
def createOptions(sizes=2, setup='fcr', bounds=[30,150]):
    n = 0
    optionlist = []
    bsizes = []
    if setup == 'leaf':
        return None
    if 'r' in setup:
        bsizes = [(bounds[-1]-bounds[0])*((n+.5)/sizes) + bounds[0] for n in range(sizes)]
        if sizes == 1:
            optionlist = ['r']
        elif sizes == 2:
            optionlist = ['rs', 'rl']
        elif sizes == 3:
            optionlist = ['rs', 'rm', 'rl']
        else:
            raise BaseException("Too many sizes")
    if 'c' in setup:
        optionlist.insert(0,'c')
    if 'f' in setup:
        optionlist.insert(0,'f')
    
    return optionlist, np.array(bsizes)
def createStrategy(options, p1len, random=False):
    if random:
        strat = []
        for i in range(p1len):
            r = np.random.uniform(0,1,len(options))
            r = r/np.sum(r)
            strat.append(r)
        return np.transpose(strat)
    return np.array([[1/len(options)]*p1len for i in range(len(options))])
    
    
class Node:
    def __init__(self, nodedepth, numcombos=None, options=createOptions(), last_sz=0, pot_sz=1, parent=None):
        self.parent = parent
        self.pot = pot_sz
        self.investments = None #Keeps track of how much each player has put into the pot
        self.depth = nodedepth #root is 0, OOP is active at 0mod2 depth, IP at 1mod2
        self.last = last_sz # Size of last bet or raise in tree
        self.options = None # List of options available at current node
        self.sizes = None # List of sizes for raise options if available
        self.unfilled = None # Only used in nodeEV fn
        self.strategy = None # 0-1 probability for each 'hand' in each branch for active player
        self.weights = None # Weights W/ removal for each 'hand' in node
        self.evs = None # EV of each 'hand' at node
        self.branchevs = [] # EV's of each branch. Sum of these will equal .evs
        self.freq = None # Only defined for leaf nodes, used for quick calculation

        if options:
            self.options = options[0]
            self.sizes = options[1]
            self.strategy = createStrategy(self.options, numcombos)
            for o in self.options:
                setattr(Node, o, None)
        
    
    def __repr__(self):
        path = ''
        current = self
        while current.parent:
            for o in current.parent.options:
                if getattr(current.parent, o) == current:
                    line = o+'-'
                    path = line+path
            
            current = current.parent
        
        path = 'root-'+path
        if self.options:
            return ("Line: " + path[:-1] + " Depth: " + str(self.depth) + " Pot: " + str(self.pot) + " Options: " + str(self.options))
        else:
            return ("Line: " + path[:-1] + " Depth: " + str(self.depth) + " Leaf: " + str(self.pot))
    
    def validate(self):
        #Validates .strategy
        if type(self.strategy) != np.ndarray:
            raise TypeError("Node strategy is not numpy")
            
        if len(self.strategy) != len(self.options):
            raise IndexError(self, "Strategy does not match dimensions of options")
        for s in np.sum(self.strategy, axis=0):
            if s < 1-(10**-3) or s > 1+(10**-3):
                raise ValueError(self, "Strategy indices do not sum to 1", s)
        for s in self.strategy:
            if min(s) < 10**-6 or max(s) > 1-10**-6:
                raise ValueError(self, "Strategy not within 10**-6 and 1-10**-6")
        return True
    
class Tree:
    def __init__(self, oop, ip, board, eff_stacks=10, max_depth=3):
        #eff_stacks is the initial effective stack size assuming starting pot of 1
        self.player = [oop, ip]
        self.eff = eff_stacks
        self.root = None
        self.maxd = max_depth
        self.build_tree()
        self.ro = CreateRankOrder(self.player[0], self.player[1], board)
        self.rou = self.ro[0], self.ro[1]
        self.row = self.ro[2], self.ro[3]
        del self.ro
        self.nodeEV()
    
    def build_tree(self):
        #To-do: Limit tree by raises not depth
        self.root = Node(0, len(self.player[0].hands), options=createOptions(setup='cr'), pot_sz=1.0)
        frontier = [self.root]
        while frontier:
            pointer = frontier.pop()
            if pointer.pot < 2*self.eff and pointer.depth < self.maxd:
                for o in pointer.options:
                    if o == 'f':
                        setattr(pointer, o, Node(pointer.depth+1, options=None, last_sz=pointer.last, pot_sz=pointer.pot, parent=pointer))
                    if o == 'c':
                        if pointer != self.root:
                            setattr(pointer, o, Node(pointer.depth+1, options=None, last_sz=pointer.last, pot_sz=pointer.pot+pointer.last, parent=pointer))
                        else:
                            setattr(pointer, o, Node(1, len(self.player[1].hands), options=createOptions(setup='cr'), pot_sz=pointer.pot+pointer.last, parent=pointer))
                            frontier.append(getattr(pointer, o))
                    if 'r' in o:
                        temp = [len(self.player[0].hands), len(self.player[1].hands)]
                        
                        if o == 'r' or o == 'rs':
                            sz = (pointer.sizes[0]/100) * (pointer.pot + pointer.last) + pointer.last
                        elif o == 'rl':
                            sz = (pointer.sizes[-1]/100) * (pointer.pot + pointer.last) + pointer.last
                        elif o == 'rm':
                            sz = (pointer.sizes[1]/100) * (pointer.pot + pointer.last) + pointer.last
                            
                        if 2*sz - pointer.last + pointer.pot > 2*self.eff:
                            sz = (2*self.eff - pointer.pot + pointer.last)/2
                            setattr(pointer, o, Node(pointer.depth+1, temp[(pointer.depth+1)%2], options=createOptions(setup='fc'), last_sz=sz-pointer.last, pot_sz=sz+pointer.pot, parent=pointer))
                            
                        elif pointer.depth == self.maxd - 2:
                            setattr(pointer, o, Node(pointer.depth+1, temp[(pointer.depth+1)%2], options=createOptions(setup='fc'), last_sz=sz-pointer.last, pot_sz=sz+pointer.pot, parent=pointer))
                        
                        else:
                            setattr(pointer, o, Node(pointer.depth+1, temp[(pointer.depth+1)%2], last_sz=sz-pointer.last, pot_sz=sz+pointer.pot, parent=pointer))
                        frontier.append(getattr(pointer, o))
        
        self.addInvestments()
    
    def addInvestments(self):
        #top-down
        frontier = [self.root]
        self.root.investments = [0, 0]
        while frontier:
            pointer = frontier.pop()
            for o in pointer.options:
                temp = getattr(pointer, o)
                if o == 'f':
                    temp.investments = pointer.investments
                    setattr(pointer, o, temp)
                elif o == 'c' and pointer.depth != 0:
                    if temp.depth%2 == 0:
                        temp.investments = [pointer.investments[0], pointer.investments[1] + temp.last]
                    else:
                        temp.investments = [pointer.investments[0] + temp.last, pointer.investments[1]]
                    setattr(pointer, o, temp)
                else:
                    if temp.depth%2 == 0:
                        temp.investments = pointer.investments[0], pointer.investments[1] + temp.last + pointer.last
                    else:
                        temp.investments = pointer.investments[0] + temp.last + pointer.last, pointer.investments[1]
                    setattr(pointer, o, temp)
                    frontier.append(getattr(pointer, o))

    
    def adjust(self):
        #Adjust sizes
        for i in range(self.maxd):
            nodes = self.getnodes(self.root, depth=i+1)
            for node in nodes:
                
                for o in node.parent.options:
                    if node == getattr(node.parent, o):
                        line = o
            
                if 'r' in line:
                    for s in node.parent.sizes:
                        if (1+.02*s)*(node.parent.pot + node.parent.last) > 2*self.eff:
                            limit = 50*(2*self.eff - (node.parent.pot+node.parent.last))/(node.parent.pot+node.parent.last)
                            node.parent.sizes = np.where(node.parent.sizes > limit, limit, node.parent.sizes)
                        
                        if .01*s*(node.parent.pot + node.parent.last) < node.parent.last:
                            limit = 100*node.parent.last/(node.parent.last + node.parent.pot)
                            node.parent.sizes = np.where(node.parent.sizes < limit, limit, node.parent.sizes)
                
                    if line == 'r' or line == 'rs':
                        node.pot = (1 + (node.parent.sizes[0]/100))*(node.parent.pot + node.parent.last)
                    elif line == 'rl':
                        node.pot = (1 + (node.parent.sizes[-1]/100))*(node.parent.pot + node.parent.last)
                    elif line == 'rm':
                        node.pot = (1 + (node.parent.sizes[1]/100))*(node.parent.pot + node.parent.last)
                    
                    node.last = node.pot - (node.parent.pot + node.parent.last)
                
                elif line == 'c':
                    node.last = node.parent.last
                    node.pot = min(node.parent.pot + node.last, 2*self.eff)
                elif line == 'f':
                    node.last = node.parent.last
                    node.pot = node.parent.pot
        
        self.addInvestments()
        self.nodeEV()
        
        
    
    def populateWeights(self):
        # Resets and fills weights
        self.root.weights = [self.player[0].initweights, self.player[1].initweights]
        frontier = [self.root]
        while frontier:
            pointer = frontier.pop()
            for o in pointer.options:
                temp = getattr(pointer, o)
                if pointer.depth % 2 == 0:
                    temp.weights = [pointer.weights[0] * pointer.strategy[pointer.options.index(o)], pointer.weights[1]]
                else:
                    temp.weights = [pointer.weights[0], pointer.weights[1] * pointer.strategy[pointer.options.index(o)]]
                    
                setattr(pointer, o, temp)
                if (o == 'c' and pointer.depth == 0) or 'r' in o:
                    frontier.append(getattr(pointer, o))
        
    def clearEVs(self):
        # Resets evs and branchevs for each node
        frontier = [self.root]
        while frontier:
            pointer = frontier.pop()
            pointer.evs = [np.zeros(len(pointer.weights[0])), np.zeros(len(pointer.weights[1]))]
            pointer.branchevs = []
            for o in pointer.options:
                if getattr(pointer, o).options == None:
                    getattr(pointer, o).evs = [np.zeros(len(pointer.weights[0])), np.zeros(len(pointer.weights[1]))]
                        
                if 'r' in o or pointer == self.root:
                    frontier.append(getattr(pointer, o))
                    
    
    def prune(self, node):
        #Deattaches node from tree
        #Changes resulting options, sizes, and strategy
        if node == self.root:
            raise BaseException("Can't prune root")
        
        for o in node.parent.options:
            if getattr(node.parent, o) == node:
                line = o
                lineindex = node.parent.options.index(o)
                setattr(node.parent, o, None)
                node.parent.options.remove(line)
                node.parent.sizes = np.delete(node.parent.sizes, lineindex-node.parent.options.count('f')-1, axis=0)
                node.parent.strategy = np.delete(node.parent.strategy, lineindex, axis=0)
                node.parent.strategy /= np.sum(node.parent.strategy, axis=0)
        
        self.nodeEV()
        
    
    def nodeEV(self):
        #Well optimized via numpy.
        #Meat and potatoes of the solver - Most of the calculation time goes on here.
        #Goes to all leaf nodes, gets the leaf EVs, and then populates parent node EVs all
        #the way up to root
        self.populateWeights()
        self.clearEVs()
        frontier = [self.root]
        #Incomplete and complete lists keep track of nodes visited for later to only visit each
        #node once
        incomplete = []
        complete = []
        #First loop goes to all nodes whose children are leaf nodes (secleaves), and gets their EVs.
        while frontier:
            pointer = frontier.pop()
            pointer.unfilled = [o for o in pointer.options]
            if pointer.options == ['f', 'c']:
                complete.append(pointer)
            else:
                incomplete.append(pointer)
            for o in pointer.options:
                if o == 'f':
                    leaf = getattr(pointer, o)
                    # leaf.freq Calculates removal-adjusted frequency
                    leaf.freq = self.rou[0].dot(leaf.weights[1]), self.rou[1].dot(leaf.weights[0])
                    if leaf.depth%2 == 0:
                        pointer.evs = [((leaf.pot)*leaf.weights[0]*leaf.freq[0]), np.zeros(len(pointer.weights[1]))]
                    else:
                        pointer.evs = [np.zeros(len(pointer.weights[0])), (leaf.pot)*leaf.weights[1]*leaf.freq[1]]
                    leaf.evs = pointer.evs
                    pointer.branchevs.append(leaf.evs[pointer.depth%2])
                    pointer.unfilled.remove(o)
                    
                elif o == 'c' and pointer.depth != 0:
                    leaf = getattr(pointer, o)
                    leaf.freq = self.rou[0].dot(leaf.weights[1]), self.rou[1].dot(leaf.weights[0])
                    leaf.evs = self.row[0].dot(leaf.weights[1])*leaf.pot*leaf.weights[0], self.row[1].dot(leaf.weights[0])*leaf.pot*leaf.weights[1]
                    if pointer == self.root.c:
                        pointer.evs = leaf.evs
                        pointer.branchevs.append(leaf.evs[pointer.depth%2])
                    else:
                        if leaf.depth%2 == 0:
                            weightedbet = ((leaf.investments[1]-pointer.investments[1])*leaf.freq[1])*leaf.weights[1]
                            pointer.evs = [pointer.evs[0] + leaf.evs[0], pointer.evs[1] + leaf.evs[1] - weightedbet]
                        else:
                            weightedbet = ((leaf.investments[0]-pointer.investments[0])*leaf.freq[0])*leaf.weights[0]
                            pointer.evs = [pointer.evs[0] + leaf.evs[0] - weightedbet, pointer.evs[1] + leaf.evs[1]]
                        
                        pointer.branchevs.append(leaf.evs[pointer.depth%2] - weightedbet)
                    pointer.unfilled.remove(o)
                else:
                    frontier.append(getattr(pointer, o))
                    
        while complete != [self.root]:
            #Here we calculate evs in nodes up the tree.
            #Once a node is 'filled' (all of its branches have the correct EVs)
            #We can fill the respective EV branch of its parent.
            for c in range(len(complete)):
                pointer = complete[c]
                parent = pointer.parent
                if pointer.depth%2 == 0:
                    weightedbet = (pointer.investments[1]-parent.investments[1])*pointer.weights[1]*self.rou[1].dot(pointer.weights[0])
                    parent.evs = [parent.evs[0] + pointer.evs[0], parent.evs[1] + pointer.evs[1] - weightedbet]
                else:
                    weightedbet = (pointer.investments[0]-parent.investments[0])*pointer.weights[0]*self.rou[0].dot(pointer.weights[1])
                    parent.evs = [parent.evs[0] + pointer.evs[0] - weightedbet, parent.evs[1] + pointer.evs[1]]
                
                #evs need to match to options; currently this appends in opposite order after f and c, so this line fixes that
                if parent == self.root:
                    parent.branchevs.insert(0, pointer.evs[parent.depth%2] - weightedbet)
                else:
                    parent.branchevs.insert(parent.options.count('f')+parent.options.count('c'), pointer.evs[parent.depth%2] - weightedbet)
                for line in parent.unfilled:
                    if getattr(parent, line) == pointer:
                        l = line
                        
                parent.unfilled.remove(l)
            
            complete = [inc for inc in incomplete if not inc.unfilled]
            incomplete = [inc for inc in incomplete if inc.unfilled]
    
    def getnodes(self, node, onode=False,inode=False,leaf=False,secleaf=False,depth=-1):
        # onode and inode refers to nodes with 0mod2(oop) and 1mod2(ip) depth respectively
        # leaf = leaf nodes, secleaf = leaves where all of its children are leaves.
        # depth returns all nodes at a certain depth, if depth >= 0.
        if not node.options:
            return None
        
        if depth >= 0:
            onode=True
            inode=True
            leaf=True
            secleaf=False
        if onode:
            onodes = []
        if inode:
            inodes = []
        if leaf:
            leaves = []
        if secleaf:
            secleaves = []
            
        frontier = [node]
        while frontier:
            pointer = frontier.pop()
            if pointer.options == ['f', 'c'] and secleaf:
                secleaves.append(pointer)
            if pointer.depth%2==0 and onode:
                onodes.append(pointer)
            if pointer.depth%2==1 and inode:
                inodes.append(pointer)
                
            for o in pointer.options:
                if 'r' in o or pointer == self.root:
                    frontier.append(getattr(pointer, o))
                elif leaf:
                    leaves.append(getattr(pointer, o))
        ret = []
        if onode:
            for node in onodes:
                ret.append(node)
        if inode:
            for node in inodes:
                ret.append(node)
        if leaf:
            for node in leaves:
                ret.append(node)
        if secleaf:
            for node in secleaves:
                ret.append(node)
        
        if len(ret) == 1:
            ret = ret[0]
            
        if depth >= 0:
            ret = [node for node in ret if node.depth == depth]
        
        return ret
    
    def rs(self):
        #Used to randomize tree's strategy
        frontier = [self.root]
        lens = [len(self.player[0].hands), len(self.player[1].hands)]
        while frontier:
            pointer = frontier.pop()
            pointer.strategy = createStrategy(pointer.options,lens[pointer.depth%2], True)
            for o in pointer.options:
                if getattr(pointer, o).options:
                    frontier.append(getattr(pointer, o))
    
