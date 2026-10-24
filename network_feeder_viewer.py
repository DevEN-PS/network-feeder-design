"""
Network Feeder Design (Rubber Tree Feeder Viewer)
================================================
An interactive power grid distribution feeder network visualizer built with
NetworkX, Pandas, and PyVis (Vis.js).

Features:
- Auto-generates realistic sample nodes.csv and branches.csv if none are present.
- BFS tree hierarchy leveling starting from the Root Substation ('SS').
- Voltage level color coding and dynamic node sizing (400kV, 220kV, 132kV, 33kV, etc.).
- Barnes-Hut elastic rubber physics with dynamic curved transmission lines.
- Drag-and-drop interactive web view saved directly to 'network.html'.
"""

import sys
from pathlib import Path
from collections import deque
import pandas as pd
import networkx as nx
from pyvis.network import Network

BASE = Path(__file__).parent.resolve()
NODES_FILE = BASE / "nodes.csv"
BRANCHES_FILE = BASE / "branches.csv"
OUTPUT_HTML = BASE / "network.html"


def generate_sample_data():
    """Generates realistic sample power distribution feeder CSV datasets if missing."""
    print("Generating sample electrical network datasets...")

    sample_nodes = [
        # bus_id, label, kv
        ("SS_CENTRAL_400", "Central Bulk Power Substation", "400"),
        ("BUS_400_NORTH", "North Ring 400kV Bus", "400"),
        ("BUS_400_SOUTH", "South Ring 400kV Bus", "400"),
        ("SS_220_IND", "Industrial Corridor 220kV Substation", "220"),
        ("SS_220_WEST", "West Valley 220kV Substation", "220"),
        ("SS_220_EAST", "East Bay 220kV Substation", "220"),
        ("BUS_132_METRO", "Metro Transit 132kV Feeder", "132"),
        ("BUS_132_TECH", "Tech Park 132kV Feeder", "132"),
        ("BUS_132_RES_A", "Residential Zone 132kV Substation", "132"),
        ("BUS_132_RES_B", "Greenfield 132kV Substation", "132"),
        ("BUS_132_PORT", "Harbor Dock 132kV Substation", "132"),
        ("FEEDER_33_A1", "Commercial Mall 33kV Feeder", "33"),
        ("FEEDER_33_A2", "Hospital Medical 33kV Feeder", "33"),
        ("FEEDER_33_B1", "Suburban North 33kV Line", "33"),
        ("FEEDER_33_B2", "Suburban South 33kV Line", "33"),
        ("FEEDER_33_SOLAR", "Solar Farm 33kV Collector", "33"),
        ("FEEDER_33_WIND", "Wind Farm 33kV Collector", "33"),
        ("FEEDER_33_IND1", "Steel Rolling Mill 33kV", "33"),
        ("FEEDER_33_IND2", "Chemical Plant 33kV", "33"),
        ("DIST_11_TOWN", "Old Town 11kV Feeder", "11"),
        ("DIST_11_UNIV", "University Campus 11kV Feeder", "11"),
        ("DIST_11_WATER", "Water Pumping Station 11kV", "11")
    ]

    sample_branches = [
        # from, to
        ("SS_CENTRAL_400", "BUS_400_NORTH"),
        ("SS_CENTRAL_400", "BUS_400_SOUTH"),
        ("BUS_400_NORTH", "BUS_400_SOUTH"),
        ("BUS_400_NORTH", "SS_220_IND"),
        ("BUS_400_NORTH", "SS_220_WEST"),
        ("BUS_400_SOUTH", "SS_220_EAST"),
        ("SS_220_IND", "BUS_132_METRO"),
        ("SS_220_IND", "BUS_132_TECH"),
        ("SS_220_WEST", "BUS_132_RES_A"),
        ("SS_220_WEST", "BUS_132_PORT"),
        ("SS_220_EAST", "BUS_132_RES_B"),
        ("BUS_132_METRO", "FEEDER_33_A1"),
        ("BUS_132_METRO", "FEEDER_33_A2"),
        ("BUS_132_TECH", "FEEDER_33_SOLAR"),
        ("BUS_132_TECH", "FEEDER_33_IND1"),
        ("BUS_132_PORT", "FEEDER_33_IND2"),
        ("BUS_132_RES_A", "FEEDER_33_B1"),
        ("BUS_132_RES_B", "FEEDER_33_B2"),
        ("BUS_132_RES_B", "FEEDER_33_WIND"),
        ("FEEDER_33_B1", "DIST_11_TOWN"),
        ("FEEDER_33_A2", "DIST_11_UNIV"),
        ("FEEDER_33_A1", "DIST_11_WATER")
    ]

    df_nodes = pd.DataFrame(sample_nodes, columns=["bus_id", "label", "kv"])
    df_nodes.to_csv(NODES_FILE, index=False)
    print(f"  -> Created: {NODES_FILE.name} ({len(sample_nodes)} buses)")

    df_branches = pd.DataFrame(sample_branches, columns=["from", "to"])
    df_branches.to_csv(BRANCHES_FILE, index=False)
    print(f"  -> Created: {BRANCHES_FILE.name} ({len(sample_branches)} branches)")


def load_datasets():
    """Loads nodes and branches, creating defaults if missing."""
    if not NODES_FILE.exists() or not BRANCHES_FILE.exists():
        generate_sample_data()

    print(f"Loading nodes from {NODES_FILE.name}...")
    nodes_df = pd.read_csv(NODES_FILE, dtype=str).fillna("")

    print(f"Loading branches from {BRANCHES_FILE.name}...")
    branches_df = pd.read_csv(BRANCHES_FILE, dtype=str).fillna("")

    print(f"  - Nodes loaded:    {len(nodes_df)}")
    print(f"  - Branches loaded: {len(branches_df)}")
    return nodes_df, branches_df


def build_graph(nodes_df, branches_df):
    """Constructs NetworkX graph and node metadata dictionary."""
    G = nx.Graph()
    node_info = {}

    for _, row in nodes_df.iterrows():
        bus_id = str(row.iloc[0]).strip()
        label = str(row.iloc[1]).strip() if len(row) > 1 else bus_id
        kv = str(row.iloc[2]).strip() if len(row) > 2 else ""

        node_info[bus_id] = (label, kv)
        G.add_node(bus_id)

    for _, row in branches_df.iterrows():
        frm = str(row["from"]).strip()
        to = str(row["to"]).strip()
        if frm and to:
            G.add_edge(frm, to)

    return G, node_info


def find_root_substation(G, node_info):
    """Finds primary root substation (containing 'SS' or first node)."""
    for bus_id, (label, kv) in node_info.items():
        txt = f"{bus_id} {label}".upper()
        if "SS" in txt:
            return bus_id

    nodes = list(G.nodes())
    return nodes[0] if nodes else None


def compute_bfs_levels(G, root):
    """Calculates hierarchical tier levels using BFS traversal, handling islands."""
    levels = {}
    visited = set()

    queue = deque()
    queue.append((root, 0))

    while queue:
        node, level = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        levels.setdefault(level, []).append(node)

        for nbr in sorted(G.neighbors(node)):
            if nbr not in visited:
                queue.append((nbr, level + 1))

    # Handle disconnected microgrid islands
    remaining = set(G.nodes()) - visited
    extra_level = (max(levels.keys()) + 2) if levels else 0

    while remaining:
        island_root = list(remaining)[0]
        queue = deque([(island_root, extra_level)])

        while queue:
            node, level = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            levels.setdefault(level, []).append(node)

            for nbr in G.neighbors(node):
                if nbr not in visited:
                    queue.append((nbr, level + 1))

        remaining = set(G.nodes()) - visited
        extra_level += 2

    return levels


def compute_tree_positions(levels, x_spacing=180, y_spacing=220):
    """Calculates symmetric geometric coordinates for each level."""
    positions = {}
    for level in sorted(levels.keys()):
        buses = levels[level]
        count = len(buses)
        start_x = -((count - 1) * x_spacing) / 2

        for i, bus in enumerate(buses):
            x = start_x + (i * x_spacing)
            y = level * y_spacing
            positions[bus] = (x, y)

    return positions


def get_voltage_style(kv_str, is_root=False):
    """Returns color hex and node diameter based on voltage level."""
    if is_root:
        return "#FF3333", 35  # Root Substation Red

    color = "#AAAAAA"
    size = 12

    try:
        kvf = float(kv_str)
        if kvf >= 400:
            color = "#00FFFF"  # 400kV+ Cyan
            size = 28
        elif kvf >= 220:
            color = "#00FF00"  # 220kV+ Neon Green
            size = 22
        elif kvf >= 132:
            color = "#FFFF00"  # 132kV+ Yellow
            size = 18
        elif kvf >= 33:
            color = "#FFA500"  # 33kV+ Orange
            size = 14
        elif kvf >= 11:
            color = "#FF7043"  # 11kV Coral
            size = 13
    except ValueError:
        pass

    return color, size


def build_pyvis_network(G, node_info, positions, root):
    """Initializes PyVis Network and binds nodes, edges, and Barnes-Hut physics."""
    net = Network(
        height="1000px",
        width="100%",
        bgcolor="#111111",
        font_color="white",
        directed=False
    )

    # Add Nodes
    for bus in G.nodes():
        label, kv = node_info.get(bus, (bus, ""))
        x, y = positions.get(bus, (0, 0))
        is_root = (bus == root)
        color, size = get_voltage_style(kv, is_root=is_root)

        tooltip = f"<b>{label}</b><br>Bus ID: <code>{bus}</code><br>Voltage: <b>{kv} kV</b>"
        if is_root:
            tooltip += "<br><span style='color:#FF3333;'>★ Root Bulk Power Substation</span>"

        net.add_node(
            bus,
            label=label,
            title=tooltip,
            x=float(x),
            y=float(y),
            physics=True,
            color=color,
            size=size
        )

    # Add Edges
    for u, v in G.edges():
        net.add_edge(
            u,
            v,
            color="#555555",
            width=2,
            physics=True
        )

    # Dynamic Barnes-Hut Rubber Physics Configuration
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -2500,
          "centralGravity": 0.03,
          "springLength": 140,
          "springConstant": 0.01,
          "damping": 0.45
        },
        "solver": "barnesHut",
        "stabilization": {
          "enabled": true,
          "iterations": 400
        }
      },
      "interaction": {
        "hover": true,
        "dragNodes": true,
        "dragView": true,
        "zoomView": true
      },
      "nodes": {
        "font": {
          "size": 12,
          "color": "#ffffff"
        }
      },
      "edges": {
        "smooth": {
          "enabled": true,
          "type": "dynamic"
        }
      }
    }
    """)

    return net


def main():
    print("=" * 60)
    print("NETWORK FEEDER DESIGN — RUBBER TREE FEEDER VIEWER")
    print("=" * 60)

    nodes_df, branches_df = load_datasets()
    G, node_info = build_graph(nodes_df, branches_df)

    root = find_root_substation(G, node_info)
    print(f"\nRoot Substation identified: {root}")

    levels = compute_bfs_levels(G, root)
    print(f"Hierarchical Feeder Tiers : {len(levels)} levels")

    positions = compute_tree_positions(levels)
    net = build_pyvis_network(G, node_info, positions, root)

    print(f"\nGenerating interactive HTML viewer: {OUTPUT_HTML.name}...")
    net.save_graph(str(OUTPUT_HTML))

    print("\n" + "=" * 60)
    print("SUCCESSFUL!")
    print(f"Buses Loaded   : {G.number_of_nodes()}")
    print(f"Branches Loaded: {G.number_of_edges()}")
    print(f"Output File    : {OUTPUT_HTML.name}")
    print("Open 'network.html' in your browser to explore.")
    print("=" * 60)


if __name__ == "__main__":
    main()
