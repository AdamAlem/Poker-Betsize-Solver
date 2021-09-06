import sizetree

class Solver:
    def __init__(self, tree):
        self.tree = tree
        self.onodes = tree.getnodes(tree.root, onode=True) #Nodes with OOP as the active player
        self.inodes = tree.getnodes(tree.root, inode=True) #Nodes with IP as the active player
        self.cost = None
    
    def getEVs(self, node, bycombo=False):
        #Returns EVs for both players for given node
        #bycombo returns EVs for each hand
        if bycombo:
            oop = node.evs[0]/(node.weights[0]*self.tree.rou[0].dot(node.weights[1]))
            ip = node.evs[1]/(node.weights[1]*self.tree.rou[1].dot(node.weights[0]))
            return oop, ip
        else:
            oop = np.sum(node.evs[0])/np.sum(node.weights[0]*self.tree.rou[0].dot(node.weights[1]))
            ip = np.sum(node.evs[1])/np.sum(node.weights[1]*self.tree.rou[1].dot(node.weights[0]))
            return np.sum(oop), np.sum(ip)
        
    def totalstrat(self, node):
        #Returns the frequency that each branch is taken at a given node
        return np.sum(node.strategy, axis=1)/np.sum(node.strategy)
    
    def getCost(self, players=[0,1], total=True):
        # Cost function of solver
        # Returns the EV difference of best line taken from root for each combo, and the actual.
        regrets = []
        for pos in players:
            handevs = []
            for i in range(len(self.tree.root.evs[pos])):
                frontier = [self.tree.root]
                ev = 0
                while frontier:
                    pointer = frontier.pop()
                    if pointer.options:
                        if pointer.depth%2 == pos:
                            best = np.argmax((np.transpose(pointer.branchevs / pointer.strategy)[i]), axis=0)
                            frontier.append(getattr(pointer, pointer.options[best]))
                        
                        else:
                            for o in pointer.options:
                                frontier.append(getattr(pointer, o))
                    
                    else:
                        ev += (pointer.evs[pos][i] / pointer.weights[pos][i]) - (pointer.investments[pos]*pointer.freq[pos][i])

                
                handevs.append(ev*self.tree.player[pos].initweights[i] - self.tree.root.evs[pos][i])
            if total:
                regrets.append(np.sum(handevs))
            else:
                regrets.append(handevs)
        return regrets
      
    def prune(self, node):
    #Deattaches node from tree
    #Changes resulting options, sizes, and strategy
        if node == self.tree.root:
            raise BaseException("Can't prune root")
        
        for o in node.parent.options:
            if getattr(node.parent, o) == node:
                line = o
                lineindex = node.parent.options.index(o)
                setattr(node.parent, line, None)
                node.parent.options.remove(line)
                node.parent.sizes = np.delete(node.parent.sizes, lineindex-node.parent.options.count('f')-1, axis=0)
                node.parent.strategy = np.delete(node.parent.strategy, lineindex, axis=0)
                node.parent.strategy /= np.sum(node.parent.strategy, axis=0)
        
        self.onodes = tree.getnodes(tree.root, onode=True)
        self.inodes = tree.getnodes(tree.root, inode=True)
        
        self.tree.nodeEV()
    
    
    def step(self, node, lr=.4, exp=.7):
        #Steps strategy in direction of -gradient of cost fn 
        
        try:
            grad = node.branchevs / node.strategy
        except ValueError:
            print(node)
        grad -= np.max(grad, axis=0)
        #Normalization
        grad /= node.weights[node.depth%2]*self.tree.rou[node.depth%2].dot(self.tree.root.weights[(node.depth+1)%2])
        grad = lr*np.array(grad)
        
        #exponential weighting
        old = np.sum(grad, axis=0)
        grad /= old
        grad = np.where(grad!=0, grad ** exp, 0)
        grad /= np.sum(grad, axis=0)
        grad *= old
        
        
        mini = np.split(np.argsort(grad, axis=0), len(node.options))
        portion = np.ones(len(node.weights[node.depth%2]))
        
        #Takes largest gradient, applies it to corresponding strategy until either the 
        #amount is filled, or the strategy equals .0001. In the latter case, it keeps track
        #of the portion filled and applies it to the next worst strategy and so on.
        while len(mini) > 1 and np.max(portion) > 0:
            mgrad = np.take_along_axis(grad, mini[0], axis=0)
            agrad = np.zeros_like(grad)
            mgrad *= portion
            np.put_along_axis(agrad, mini[0], mgrad, axis=0)
            portion = np.where(-agrad > node.strategy-.0001, portion + np.divide((node.strategy-.0001),agrad, where=agrad!=0), 0)
            node.strategy = np.where(-agrad > node.strategy-.0001, .0001, node.strategy + agrad)
            portion = np.max(portion, axis=0)
            mini.pop(0)
        
        sums = 1-np.sum(node.strategy, axis=0) + np.take_along_axis(node.strategy, mini[-1], axis=0)
        np.put_along_axis(node.strategy, mini[-1], sums, axis=0)
        
        
    def treeloop(self, lr=.4, exp=.7):
        onodes = [node for node in self.onodes]
        inodes = [node for node in self.inodes]
        #Applies step to all nodes of OOP then IP
        
        while onodes:
            onode = onodes.pop()
            self.step(onode, lr, exp)
        self.tree.nodeEV()
        while inodes:
            inode = inodes.pop()
            self.step(inode, lr, exp)
        self.tree.nodeEV()
    
    
    def sizestep(self, nodes):
        # Experimental gradient method for bet sizes
        # Seems to work reasonably well with pruning.
        for node in nodes:
            if node.sizes.size > 0 and np.sum(node.weights[node.depth%2]*self.tree.rou[node.depth%2].dot(node.weights[(node.depth+1)%2])) > .01 * 3**-(node.depth+1):
                grad = []
                for o in node.options:
                    if self.totalstrat(node)[node.options.index(o)] > .01:
                        if 'r' in o:
                            branch = getattr(node, o)
                            fe = self.totalstrat(branch)[0]
                            comboevs = self.getEVs(branch, bycombo=True)[branch.depth%2]
                            mincost = np.nanmin(np.where(branch.strategy[0] > .999, np.nan, comboevs/(1-branch.strategy[0])))
                            actioncost = self.getEVs(branch)[branch.depth%2] / (1-fe)
                            g = (branch.pot - branch.last) - (2*actioncost - mincost) #The gradient
                            g /= branch.pot
                            g = min(max((1/(1+1.4**-g))+0.5, .667), 1.5)
                            grad.append(g)
                    
                    elif 'r' in o:
                        grad.append(1)
                        
                node.sizes = node.sizes * grad
                node.sizes = np.where(node.sizes < 10, 10, node.sizes)
                node.sizes = np.where(node.sizes > 1000, 1000, node.sizes)
                        
                        
        
        self.tree.adjust()
    
    def SizeSolve(self, n=20):

        for i in range(n):
            self.sizestep(self.onodes)
            self.Solve()
            self.sizestep(self.inodes)
            self.Solve()
            
        self.showsizes()
    
    def showgrad(self, node):
        grad = []
        for o in node.options:
            if 'r' in o:
                branch = getattr(node, o)
                fe = self.totalstrat(branch)[0]
                comboevs = self.getEVs(branch, bycombo=True)[branch.depth%2]
                mincost = np.nanmin(np.where(branch.strategy[0] > .999, np.nan, comboevs/(1-branch.strategy[0])))
                actioncost = self.getEVs(branch)[branch.depth%2] / (1-fe)
                g = (branch.pot - branch.last) - (2*actioncost - mincost) #The gradient
                g /= branch.pot
                grad.append(g)
        
        return grad
    
    def showsizes(self):
        
        for i in range(self.tree.maxd+1):
            
            onode = [node for node in self.onodes if node.depth == i]
            inode = [node for node in self.inodes if node.depth == i]
            
            for node in onode:
                if node.sizes.size > 0:
                    print(node.__repr__()[:node.__repr__().rfind('D')], "Sizes: ", node.sizes, "Freq: ", np.sum(node.weights[node.depth%2]*self.tree.rou[node.depth%2].dot(node.weights[(node.depth+1)%2])), "Betting Freq:", self.totalstrat(node)[-len(node.sizes):])
    
            
            for node in inode:
                if node.sizes.size > 0:
                    print(node.__repr__()[:node.__repr__().rfind('D')], "Sizes: ", node.sizes, "Freq: ", np.sum(node.weights[node.depth%2]*self.tree.rou[node.depth%2].dot(node.weights[(node.depth+1)%2])), "Betting Freq:", self.totalstrat(node)[-len(node.sizes):])

    
    def Solve(self, n=100, lr=.4, exp=.7, goal=.01):
        # n applies treeloop n times if goal is not met
        # lr and exp are the learning rate and exponential weighting used in step
        # Goal signifies how low we want the cost function to be before we stop.
        
        for i in range(n):
            self.treeloop(lr=lr, exp=exp)
            if i % 10 == 9:
                cost = self.getCost()
                if np.sum(cost) < goal:
                    return cost
        return self.getCost()

        


    