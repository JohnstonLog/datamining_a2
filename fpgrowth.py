# FP-Growth — CPSC 473/673 A2
# Usage:  python fpgrowth.py <dataset_path> <minsup_percent>
# Output: MiningResult_<datasetFileName>.txt with:
#         first line "|FPs| = N", then "a, b, c : support"
import sys, os, math, time
from collections import defaultdict


def load_transactions(path):
    txns = []
    header_checked = False

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            # Skip a single integer header if present on the first non-empty line
            if not header_checked:
                header_checked = True
                parts0 = line.split()
                if len(parts0) == 1 and parts0[0].lstrip("+-").isdigit():
                    continue

            parts = line.split()
            if len(parts) >= 3 and parts[1].lstrip("+-").isdigit():
                items = parts[2:]
            else:
                items = parts

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
        self.link = None


class FPTree:
    def __init__(self, transactions, minsup):
        self.transactions = transactions
        self.minsup = minsup
        self.header_table = {}       # item -> first node in chain
        self.root = FPNode(None, 0, None)
        self.frequent_items = {}     # item -> global support
        self.build_fptree()

    def build_fptree(self):
        # Pass 1: global counts (once per transaction)
        item_counts = {}
        for t in self.transactions:
            for itm in t:
                item_counts[itm] = item_counts.get(itm, 0) + 1

        # Keep only items meeting minsup
        self.frequent_items = {i: c for i, c in item_counts.items() if c >= self.minsup}
        if not self.frequent_items:
            self.transactions = None
            return

        # Sort by support (desc)
        self.frequent_items = dict(sorted(self.frequent_items.items(), key=lambda x: x[1], reverse=True))

        # Pass 2: build the tree; tie-break by item id for determinism
        def order_key(x):
            return (-self.frequent_items[x], str(x))

        for t in self.transactions:
            filt = [x for x in t if x in self.frequent_items]
            if not filt:
                continue
            ordered = sorted(filt, key=order_key)
            self._insert(ordered, self.root)

        # Free raw transactions; tree + headers are sufficient
        self.transactions = None

    def _insert(self, items, node):
        if not items:
            return
        first = items[0]
        if first in node.children:
            node.children[first].count += 1
        else:
            child = FPNode(first, 1, node)
            node.children[first] = child
            if first in self.header_table:
                cur = self.header_table[first]
                while cur.link is not None:
                    cur = cur.link
                cur.link = child
            else:
                self.header_table[first] = child
        self._insert(items[1:], node.children[first])

    def _sum_header_support(self, node):
        total = 0
        cur = node
        while cur is not None:
            total += cur.count
            cur = cur.link
        return total

    def _conditional_base(self, node):
        base = []
        cur = node
        while cur is not None:
            path = []
            p = cur.parent
            while p is not None and p.item is not None:
                path.append(p.item)
                p = p.parent
            path.reverse()
            if path:
                base.append((path, cur.count))
            cur = cur.link
        return base

    def _build_conditional_tree(self, patterns, minsup):
        # Weighted local counts in conditional base
        local = defaultdict(int)
        for path, c in patterns:
            for it in set(path):
                local[it] += c

        frequent = {i: s for i, s in local.items() if s >= minsup}
        if not frequent:
            return FPTree([], minsup)

        order = sorted(frequent.items(), key=lambda x: (-x[1], x[0]))
        rank = {it: i for i, (it, _) in enumerate(order)}

        new_tree = FPTree([], minsup)
        new_tree.frequent_items = dict(order)

        for path, c in patterns:
            filt = [i for i in path if i in frequent]
            if not filt:
                continue
            filt.sort(key=lambda i: rank[i])
            node = new_tree.root
            for it in filt:
                if it in node.children:
                    node.children[it].count += c
                else:
                    child = FPNode(it, c, node)
                    node.children[it] = child
                    if it in new_tree.header_table:
                        cur = new_tree.header_table[it]
                        while cur.link is not None:
                            cur = cur.link
                        cur.link = child
                    else:
                        new_tree.header_table[it] = child
                node = node.children[it]
        return new_tree

    def mine_patterns(self):
        patterns = {}
        # Mine items from least to most frequent (standard FP-growth order)
        items = sorted(self.header_table.items(), key=lambda x: self.frequent_items[x[0]])
        for it, first_node in items:
            sup = self._sum_header_support(first_node)
            base = (it,)
            patterns[base] = sup

            cpb = self._conditional_base(first_node)
            ctree = self._build_conditional_tree(cpb, self.minsup)
            if ctree.root.children:
                sub = ctree.mine_patterns()
                for pat, cnt in sub.items():
                    merged = tuple(sorted(pat + base))
                    patterns[merged] = cnt
        return patterns


def fpgrowth(transactions, minsup):
    tree = FPTree(transactions, minsup)
    return tree.mine_patterns()


def _to_key(x):
    # Numeric-aware sort: integers first, then strings
    if isinstance(x, int):
        return (0, x)
    try:
        return (0, int(x))
    except Exception:
        return (1, str(x))


def format_itemset(itemset_tuple):
    items = sorted(itemset_tuple, key=_to_key)
    return ", ".join(map(str, items))


def write_results(outfile, patterns):
    # Order by size, then lexicographic (numeric-aware)
    def pkey(k):
        return (len(k), [_to_key(x) for x in k])
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(f"|FPs| = {len(patterns)}\n")
        for iset in sorted(patterns.keys(), key=pkey):
            f.write(f"{format_itemset(iset)} : {patterns[iset]}\n")


def main():
    if len(sys.argv) != 3:
        print("Usage: python fpgrowth.py <dataset_path> <minsup_percent>", file=sys.stderr)
        sys.exit(1)

    dataset_path = sys.argv[1]
    if not os.path.exists(dataset_path):
        print(f"Error: file not found: {dataset_path}", file=sys.stderr)
        sys.exit(1)

    try:
        minsup_percent = float(sys.argv[2])
        if not (0 < minsup_percent <= 100):
            raise ValueError
    except ValueError:
        print("Error: <minsup_percent> must be between 0 and 100.", file=sys.stderr)
        sys.exit(1)

    t0 = time.perf_counter()
    txns = load_transactions(dataset_path)
    n = len(txns)
    if n == 0:
        print("Empty dataset.")
        sys.exit(0)

    minsup_count = math.ceil((minsup_percent / 100) * n)
    print(f"minsup = {minsup_percent}% = {minsup_count}")

    patterns = fpgrowth(txns, minsup_count)

    outfile = f"MiningResult_{os.path.basename(dataset_path)}"
    write_results(outfile, patterns)
    print(f"|FPs| = {len(patterns)}")
    print(f"Total Runtime: {time.perf_counter() - t0:.3f} sec")


if __name__ == "__main__":
    main()
