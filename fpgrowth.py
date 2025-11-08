# FP-Growth Algorithm Implementation
# Define a class for the nodes in the FP-tree
import sys, os, math, time
from collections import defaultdict
from itertools import combinations

def load_transactions(path):
    """Reads dataset and returns a list of transactions as frozensets of integers.
    Supports:
      1) tid  count  item...   (ignore first two fields)
      2) item...               (use all tokens)
    Accepts mixed whitespace.
    """
    txns = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split()  # any whitespace
            # Case A: looks like tid/count format (>=3 tokens and 2nd token is int)
            if len(parts) >= 3 and parts[1].lstrip("+-").isdigit():
                items = parts[2:]
            else:
                # Case B: plain items
                items = parts
            # parse ints; fallback to raw tokens if any non-int
            try:
                itemset = frozenset(map(int, items))
            except ValueError:
                itemset = frozenset(items)
            if itemset:
                txns.append(itemset)
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
        self.header_table = {}    # item -> first node in linked chain
        self.root = FPNode(None, 0, None)
        self.frequent_items = {}  # item -> global support (for ordering)
        self.build_fptree(transactions)

    def build_fptree(self, transactions):
        # First pass: count item frequencies (1 per txn)
        item_counts = {}
        for transaction in self.transactions:
            for item in transaction:
                item_counts[item] = item_counts.get(item, 0) + 1

        # Keep only frequent items and sort by global frequency (desc)
        self.frequent_items = {
            item: count for item, count in item_counts.items() if count >= self.minsup
        }
        self.frequent_items = dict(sorted(self.frequent_items.items(), key=lambda x: x[1], reverse=True))

        # Second pass: build the FP-tree in global frequency order
        for transaction in self.transactions:
            filtered_transaction = [item for item in transaction if item in self.frequent_items]
            if not filtered_transaction:
                continue
            sorted_transaction = sorted(
                filtered_transaction,
                key=lambda x: self.frequent_items[x],
                reverse=True
            )
            self.insert_tree(sorted_transaction, self.root)

    def insert_tree(self, items, node):
        if not items:
            return
        first_item = items[0]
        if first_item in node.children:
            node.children[first_item].count += 1
        else:
            new_node = FPNode(first_item, 1, node)
            node.children[first_item] = new_node

            # Update header table (append to chain)
            if first_item in self.header_table:
                current_node = self.header_table[first_item]
                while current_node.link is not None:
                    current_node = current_node.link
                current_node.link = new_node
            else:
                self.header_table[first_item] = new_node

        self.insert_tree(items[1:], node.children[first_item])

    # ---------- NEW: helpers for correct mining ----------

    def _sum_header_support(self, node):
        """Sum counts across the entire header-linked chain for an item."""
        total = 0
        cur = node
        while cur is not None:
            total += cur.count
            cur = cur.link
        return total

    def build_conditional_tree_from_patterns(self, patterns, minsup):
        """Build a new FP-tree from a list of (path:list[item], count:int)."""
        # 1) local frequency counts (weighted)
        local_counts = defaultdict(int)
        for path, cnt in patterns:
            for it in set(path):
                local_counts[it] += cnt

        # 2) keep only locally frequent
        frequent = {i: c for i, c in local_counts.items() if c >= minsup}
        if not frequent:
            return FPTree([], minsup)  # empty

        # 3) order by local frequency (desc, then item asc for stability)
        order = sorted(frequent.items(), key=lambda x: (-x[1], x[0]))
        rank = {it: i for i, (it, _) in enumerate(order)}

        # 4) build new tree with counted insertions
        new_tree = FPTree([], minsup)
        new_tree.frequent_items = dict(order)  # provide ordering info to miner

        for path, cnt in patterns:
            filtered = [i for i in path if i in frequent]
            if not filtered:
                continue
            filtered.sort(key=lambda i: rank[i])
            node = new_tree.root
            for it in filtered:
                if it in node.children:
                    child = node.children[it]
                    child.count += cnt
                else:
                    child = FPNode(it, cnt, node)
                    node.children[it] = child
                    # header links
                    if it in new_tree.header_table:
                        cur = new_tree.header_table[it]
                        while cur.link is not None:
                            cur = cur.link
                        cur.link = child
                    else:
                        new_tree.header_table[it] = child
                node = child

        return new_tree

    # -----------------------------------------------------

    def mine_patterns(self):
        patterns = {}
        # Iterate items from least frequent to most frequent (standard backtracking order)
        items = sorted(self.header_table.items(), key=lambda x: self.frequent_items[x[0]])

        for item, first_node in items:
            # Correct singleton support = sum over the whole header chain
            base_support = self._sum_header_support(first_node)
            suffix = (item,)
            patterns[suffix] = base_support

            # Build conditional pattern base for this item
            cpb = self.find_conditional_pattern_base(first_node)  # list[(path, count)]

            # Build a conditional FP-tree from weighted paths
            ctree = self.build_conditional_tree_from_patterns(cpb, self.minsup)

            # Recurse if the conditional tree is non-empty
            if ctree.root.children:
                cpatterns = ctree.mine_patterns()
                for pat, cnt in cpatterns.items():
                    merged = tuple(sorted(pat + suffix))
                    patterns[merged] = cnt

        return patterns

    def find_conditional_pattern_base(self, node):
        conditional_pattern_base = []
        cur = node
        while cur is not None:
            path = []
            parent = cur.parent
            while parent is not None and parent.item is not None:
                path.append(parent.item)
                parent = parent.parent
            path.reverse()
            if path:
                conditional_pattern_base.append((path, cur.count))
            cur = cur.link
        return conditional_pattern_base


def fpgrowth(transactions, minsup):
    tree = FPTree(transactions, minsup)
    patterns = tree.mine_patterns()
    return patterns


# Functions to load data, build FP-tree, mine patterns, and main fpgrowth function
def build_fptree(transactions, minsup):
    return FPTree(transactions, minsup)

def mine_patterns(tree):
    return tree.mine_patterns()


# combine
def main():
    # --- Validate command-line arguments ---
    if len(sys.argv) != 3:
        print("Usage: python fpgrowth.py <dataset_path> <minsup_percent>", file=sys.stderr)
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
    if n_txn == 0:
        print("Empty dataset.")
        sys.exit(0)

    # --- Step 2: Compute minimum support count (ceiling) ---
    minsup_count = math.ceil((minsup_percent / 100) * n_txn)
    print(f"minsup = {minsup_percent}% = {minsup_count}")

    # --- Step 3: Build FP-tree and mine patterns ---
    tree = build_fptree(txns, minsup_count)
    patterns = mine_patterns(tree)

    # --- Step 4: Output results to file (kept as-is for now) ---
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
