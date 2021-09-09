# -*- coding: utf-8 -*-
"""
Created on Thu May 27 16:23:15 2021
@author: Adam
"""


board = randBoard()
p1 = Player(makeRange(100, board))
p2 = Player(makeRange(100, board))
tree = Tree(p1, p2, board, eff_stacks=12, max_depth=5)
sol = Solver(tree)
sol.SizeSolve()
