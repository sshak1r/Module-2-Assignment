import os
import csv
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import networkx as nx
import matplotlib.pyplot as plt


SEEDS = [
    "https://en.wikipedia.org/wiki/University_of_Maryland,_College_Park",
    "https://en.wikipedia.org/wiki/Higher_education",
    "https://en.wikipedia.org/wiki/Information_science",
    "https://en.wikipedia.org/wiki/Public_university",
    "https://en.wikipedia.org/wiki/College_Park,_Maryland",
]

BASE = "https://en.wikipedia.org"
HEADERS = {"User-Agent": "INST414-A2/1.0 (student project)"}


def main():
    os.makedirs("results", exist_ok=True)

    G = nx.DiGraph()

    # 1) scrape links from each seed page
    for url in SEEDS:
        print("scraping:", url)
        try:
            html = requests.get(url, headers=HEADERS, timeout=15).text
            soup = BeautifulSoup(html, "html.parser")
            content = soup.select_one("#mw-content-text")
            if not content:
                continue

            # keep only /wiki/... links (ignore Special:, File:, etc.)
            for a in content.select("a[href]"):
                href = a.get("href", "")
                if not href.startswith("/wiki/"):
                    continue
                if ":" in href:  # filters Special:, File:, Category:, etc.
                    continue

                target = urljoin(BASE, href)
                G.add_edge(url, target)

        except Exception as e:
            print("  failed:", e)

        time.sleep(1)  # be polite

    print("nodes:", G.number_of_nodes(), "edges:", G.number_of_edges())

    # 2) compute importance
    pr = nx.pagerank(G)  # PageRank
    bt = nx.betweenness_centrality(G)  # betweenness

    # 3) save top nodes table
    rows = []
    for node in G.nodes():
        rows.append(
            (
                node.replace("https://en.wikipedia.org/wiki/", "").replace("_", " "),
                node,
                G.in_degree(node),
                G.out_degree(node),
                pr.get(node, 0.0),
                bt.get(node, 0.0),
            )
        )

    rows.sort(key=lambda r: (r[4], r[5]), reverse=True)

    csv_path = "results/top_nodes.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "url", "in_degree", "out_degree", "pagerank", "betweenness"])
        for r in rows[:15]:
            w.writerow([r[0], r[1], r[2], r[3], f"{r[4]:.6f}", f"{r[5]:.6f}"])

    print("saved:", csv_path)

    # 4) draw a simple network image (just the seed pages + their immediate links)
    keep = set(SEEDS)
    for s in SEEDS:
        keep.update(list(G.successors(s))[:30])  # cap to keep image readable
    H = G.subgraph(keep).copy()

    plt.figure(figsize=(12, 9))
    pos = nx.spring_layout(H, seed=42)
    sizes = [3000 * pr.get(n, 0) + 30 for n in H.nodes()]

    nx.draw_networkx_edges(H, pos, arrows=True, alpha=0.3)
    nx.draw_networkx_nodes(H, pos, node_size=sizes, alpha=0.9)

    # short labels (page names only)
    labels = {n: n.split("/wiki/")[-1].replace("_", " ")[:18] for n in H.nodes()}
    nx.draw_networkx_labels(H, pos, labels=labels, font_size=7)

    plt.axis("off")
    plt.title('What Makes a Web Page "Important"? (PageRank + Betweenness)')
    img_path = "results/network.png"
    plt.tight_layout()
    plt.savefig(img_path, dpi=200)
    plt.close()

    print("saved:", img_path)

    # quick sanity output
    print("\nTop 5 by PageRank:")
    for r in rows[:5]:
        print("-", r[0], "PR=", round(float(r[4]), 4), "BT=", round(float(r[5]), 4))


if __name__ == "__main__":
    main()
