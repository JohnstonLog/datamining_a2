# FP-Growth Algorithm Implementation
# Define a class for the nodes in the FP-tree
import sys, os, math, time
from collections import defaultdict
from itertools import combinations

def load_transactions(path):
    """Reads dataset and returns a list of transactions as frozensets of integers."""
    txns = []
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        try:
            _n = int(header)  # number of transactions (first line)
        except ValueError:
            raise ValueError("First line must be integer (number of transactions)")
        # Read each transaction line
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue  # skip empty or malformed lines
            items = list(map(int, parts[2].split()))
            txns.append(frozenset(items))
    return txns

class FPNode:
    def __init__(self, item, count, parent):
        self.item = item
        self.count = count
        self.parent = parent
        self.children = {}
        self.link = None  # Link to next node with the same item    

# Define a class for the FP-tree
class FPTree:
    def __init__(self, transactions, minsup):
        self.transactions = transactions
        self.minsup = minsup
        self.header_table = {}
        self.root = FPNode(None, 0, None)
        self.build_fptree(transactions)

    def build_fptree(self, transactions):
        # First pass: count item frequencies
        item_counts = {}
        for transaction in self.transactions:
            for item in transaction:
                item_counts[item] = item.get(item, 0) + 1 #im having a bitch here
    
        # Filter items by minsup and sort them
        self.frequent_items = {item: count for item, count in item_counts.items() if count >= self.minsup}
        self.frequent_items = dict(sorted(self.frequent_items.items(), key=lambda x: x[1], reverse=True))

        # Second pass: build the FP-tree
        for transaction in self.transactions:
            filtered_transaction = [item for item in transaction if item in self.frequent_items]
            sorted_transaction = sorted(filtered_transaction, key=lambda x: self.frequent_items[x], reverse=True)
            self.insert_tree(sorted_transaction, self.root)

    def insert_tree(self, items, node):
        if len(items) == 0:
            return

        first_item = items[0]
        if first_item in node.children:
            node.children[first_item].count += 1
        else:
            new_node = FPNode(first_item, 1, node)
            node.children[first_item] = new_node

            # Update header table
            if first_item in self.header_table:
                current_node = self.header_table[first_item]
                while current_node.link is not None:
                    current_node = current_node.link
                current_node.link = new_node
            else:
                self.header_table[first_item] = new_node

        remaining_items = items[1:]
        self.insert_tree(remaining_items, node.children[first_item])
    def mine_patterns(self):
        patterns = {}
        items = sorted(self.header_table.items(), key=lambda x: self.frequent_items[x[0]])

        for item, node in items:
            suffix = [item]
            conditional_pattern_base = self.find_conditional_pattern_base(node)
            conditional_tree = FPTree(conditional_pattern_base, self.minsup)

            if conditional_tree.root.children:
                conditional_patterns = conditional_tree.mine_patterns()
                for pattern, count in conditional_patterns.items():
                    patterns[tuple(sorted(suffix + list(pattern)))] = count
            else:
                patterns[tuple(suffix)] = node.count

        return patterns
    
    def find_conditional_pattern_base(self, node):
        conditional_pattern_base = []
        while node is not None:
            path = []
            parent = node.parent
            while parent is not None and parent.item is not None:
                path.append(parent.item)
                parent = parent.parent
            path.reverse()
            if len(path) > 0:
                conditional_pattern_base.append((path, node.count))
            node = node.link
        return conditional_pattern_base

def fpgrowth(transactions, minsup):
    tree = FPTree(transactions, minsup)
    patterns = tree.mine_patterns()
    return patterns


# Functions to load data, build FP-tree, mine patterns, and main fpgrowth function

def build_fptree(transactions,minsup):
    return FPTree(transactions, minsup)

def mine_patterns(tree):
    return tree.mine_patterns()

#combine 

def main():       
       # --- Validate command-line arguments ---
    if len(sys.argv) != 3:
        print("Usage: python apriori.py <dataset_path> <minsup_percent>", file=sys.stderr)
        sys.exit(1)

    dataset_path = sys.argv[1]
    try:
        minsup_percent = float(sys.argv[2])
        if not (0 < minsup_percent <= 100):
            raise ValueError
    except ValueError:
        print("Error: <minsup_percent> must be between 0 and 100.", file=sys.stderr)
        sys.exit(1)

    # --- Step 1: Load transactions ---
    start_time = time.time()
    txns = load_transactions(dataset_path)
    n_txn = len(txns)

    # --- Step 2: Compute minimum support count (ceiling) ---
    minsup_count = math.ceil((minsup_percent / 100) * n_txn)
    print("minsup = {minsup_percent}% = {minsup_count}")            
    
    # --- Step 3: Build FP-tree and mine patterns ---
    tree = build_fptree(txns, minsup_count)
    patterns = mine_patterns(tree)

    # --- Step 4: Output results to file---
    output_path = os.path.splitext(dataset_path)[0] + f"_fpgrowth_{minsup_percent:.0f}.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for pattern, count in sorted(patterns.items(), key=lambda x: (-x[1], x[0])):
            pattern_str = " ".join(map(str, pattern))
            f.write(f"{pattern_str}\t{count}\n")
    end_time = time.time()
    print(f"Output written to {output_path}")
    print(f"Elapsed time: {end_time - start_time:.2f} seconds")
    print(f"Number of patterns: {len(patterns)}")   

if __name__ == "__main__":
    main()