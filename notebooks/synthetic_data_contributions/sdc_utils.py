home_dir = "/Users/cgmeyer"  # change this to your home_dir
import glob
import json
import copy
import random
import datetime
from datetime import datetime
from pathlib import Path
import pandas as pd
import uuid
import sys
import os
import glob

##########################################################################################
##########################################################################################
## SCRIPTS
##########################################################################################


def read_json(json_file):
    with open(json_file, "r") as f:
        data = json.load(f)
    return data


def get_node_links(node_def):
    links = node_def["links"]
    return links


def get_node_headers(node, dm):
    """
    If gen3_ids is False, submitter_id and id won't be added. Instead "<node>.id" will be added, which is more consistent with how data are provided by contributors.
    root_node is specified to avoid adding links to nodes above the root node in the headers (i.e., don't include the root node's links, if there are any).
    """
    node_def = get_node_def(node, dm)
    props = node_def["properties"]
    headers = [p["name"] for p in props]
    return headers


# get_node_headers('project',dm)
# get_node_headers('case',dm)
# get_node_headers(node,dm)


def get_node_backref(node, dd):
    """This function takes a node and a data dictionary and finds the "backref" for the node in links"""
    backrefs = []
    if node == "program":
        backrefs.append("programs")
    else:
        if "links" in dd[node]:
            links = dd[node]["links"]
            for link in links:
                if "subgroup" in link:
                    for sublink in link["subgroup"]:
                        if "subgroup" in sublink:
                            for subsublink in sublink["subgroup"]:
                                if "backref" in subsublink:
                                    backrefs.append(subsublink["backref"])
                        elif "backref" in sublink:
                            backrefs.append(sublink["backref"])
                elif "backref" in link:
                    backrefs.append(link["backref"])
    if len(backrefs) > 0:
        return backrefs[0]
    else:
        return None


# get_node_backref('aliquot',dd)


def get_submission_order(dm, root_node="project"):
    """
    This function takes a simplified data dictionary, and then it determines the hierarchical order of nodes by looking at the links, which is the necessary Gen3 Sheepdog submission order.
    The reverse of this is the deletion order for deleting projects via Gen3 Sheepdog API, following the principle that all records in linking child nodes must be deleted before deleting the parent records.
    Returns a dictionary with the submission order of all nodes including the root node with order 0.
    """
    nodes = [n["name"] for n in dm["nodes"]]
    suborder = {root_node: 0}
    round = 0
    while len(suborder) < len(nodes):  # "root_node" != in "nodes", thus the +1
        round += 1
        # print("\nFinding submission order, round: {}".format(round))
        for node in nodes:  # node = nodes[1]
            # print(node)
            if node not in suborder:
                # print(node)
                node_def = [nd for nd in dm["nodes"] if nd["name"] == node][0]
                parents = node_def["links"]
                if False in [i in [i for i in suborder] for i in parents]:
                    # print("\t\tSkipping Node ({}): {}".format(round,node))
                    continue  # if any parent is not already in suborder, skip this node for now
                else:  # if all parents are already in suborder, add this node after the last parent to submit
                    # print("\t\tAdding Node ({}): {}".format(round,node))
                    parents_order = [
                        item for item in suborder if item in parents
                    ]  # get existing order for each parent in list
                    suborder[node] = (
                        max([suborder[parent] for parent in parents_order]) + 1
                    )  # add the node with the max order of the parents + 1
    # suborder = sorted(suborder, key=lambda x: x[1])
    sorted_suborder = dict(sorted(suborder.items(), key=lambda item: item[1]))
    return sorted_suborder


# get_submission_order(dm)


def list_nodes(sdm):
    """
    returns the list node names for a simplified data mode
    """
    nodes = [n["name"] for n in sdm["nodes"]]
    return nodes


def get_node_links(node, dm):
    """This function takes a node name and a simplified data model and returns the list of links for that node."""
    node_def = [n for n in dm["nodes"] if n["name"] == node][0]
    links = node_def["links"]
    return links


# get_node_links(node,dm) # ['project','subject','case']


def get_node_def(node, dm):
    """Returns the node's definition in a given simplified data model"""
    node_def = [n for n in dm["nodes"] if n["name"] == node][0]
    return node_def


# get_node_def(node,dm)


def get_leaf_nodes(dm):
    """
    This function takes a simplified data model and returns a list of leaf nodes, which are nodes that do not have any children nodes.
    The leaf nodes can be found by searching for other nodes that link to them. If no other nodes in the data model link to a given node, it is a "leaf node" AKA "terminal node" or "terminus".
    """
    leaf_nodes = []
    for node in dm["nodes"]:
        node_name = node["name"]
        leaf = True
        for other_node in [n for n in dm["nodes"] if n["name"] != node_name]:
            # print(other_node)
            if "links" in other_node and node_name in other_node["links"]:
                leaf = False
                break  # if the node is a target of another node, it is not a leaf node
        if leaf:
            leaf_nodes.append(node_name)
    return leaf_nodes


# get_leaf_nodes(dm)


def get_file_nodes(dm, use_file_name=True):
    """
    This function takes a data dictionary and returns a list of data file nodes, which are nodes that have a category of 'data_file' or have an 'object_id' property.
    Option to only use presence of 'data_category' property for finding ndoes by setting 'use_ca=True'.
    """
    file_nodes = []
    for node_def in dm["nodes"]:  # node_def = dm['nodes'][1]
        # if 'category' in dd[node] and dd[node]['category'] == 'data_file':
        #     file_nodes.append(node)
        # elif 'properties' in dd[node] and 'object_id' in dd[node]['properties'] and use_object_id:
        #     file_nodes.append(node)
        if (
            use_file_name
            and "properties" in node_def
            and any(
                p["name"] for p in node_def["properties"] if p["name"] == "file_name"
            )
        ):
            file_nodes.append(node_def["name"])
    return file_nodes


# get_file_nodes(dm)


def get_node_parents(node, dm):
    """This function takes a node and a data dictionary and finds all parent nodes up to root node(s) (nodes with no links to any other nodes)."""
    parents = []
    try:
        nodes = list_nodes(dm)
        links = get_node_links(node, dm)
    except Exception as e:
        print(f"Error getting links for '{node}': {e}")
    if len(links) != 0:
        for link in links:  # link = links[0]
            if link in nodes:
                parents.append(link)
                pparents = get_node_parents(link, dm)
                parents += pparents
    # create a dictionary of parents where the keys are sorted using the order_nodes function
    ordered_parents = sorted(
        list(set(parents)), key=lambda x: get_submission_order(dm)[x]
    )
    return ordered_parents


# get_node_parents(node,dm)


def organize_headers(headers, node, dm):
    """This function takes a list of headers and organizes them in standard Gen3 submission template order.
    type, project_id, submitter_id, required_props, ubiquitous_props, file_props, other_props, link_props
    """
    node_def = get_node_def(node, dm)
    headers = list(set(headers))
    sorted_headers = []
    parents = get_node_parents(node, dm)
    foreign_keys = [f"{p}.id" for p in parents]
    sorted_headers.append(f"{node}.id")
    if "required" in node_def:
        for prop in sorted(node_def["required"]):
            if (
                prop in headers
                and prop not in sorted_headers
                and prop not in foreign_keys
            ):
                sorted_headers.append(prop)
    for prop in sorted(
        [h for h in headers if h not in sorted_headers and h not in foreign_keys]
    ):  # add any remaining props
        sorted_headers.append(prop)
    for prop in [
        h for h in foreign_keys if h not in sorted_headers and h in headers
    ]:  # add foreign keys
        sorted_headers.append(prop)
    return sorted_headers


def randomize_headers(node, dm, keep_min, keep_max, hard_limit, keep_required=False):
    """
    This function takes a node and randomly selects between keep_min to keep_max percent the properties.
    Foreign keys are always kept.
    hard_limit is implemented to keep the number of headers below a chosen threshold.
    """
    node_def = get_node_def(node, dm)
    node_name = node_def["name"]
    headers = [p["name"] for p in node_def["properties"]]
    random_headers = []  # always keep the node id

    if keep_required and "required" in node_def:
        random_headers += [
            h for h in node_def["required"] if h in headers
        ]  # keep required properties as defined in node schema
    # else: # keep only foreign keys
    #     foreign_keys = [h for h in headers if h.endswith('.id') and h != f'{node_name}.id']
    #     if len(foreign_keys) > 1:
    #         random_keys = random.sample(foreign_keys, random.randint(1, len(foreign_keys)))
    #         random_headers += random_keys
    #     else:
    #         random_headers += foreign_keys
    else:
        random_headers += [h for h in headers if h.endswith(".id")]

    optional_headers = [h for h in headers if h not in random_headers]
    # pick random int bw keep_min and keep_max to keep from optional_headers
    ikeep_min = int(len(optional_headers) * (keep_min / 100))
    ikeep_max = int(len(optional_headers) * (keep_max / 100))
    ikeep = random.randint(ikeep_min, ikeep_max)
    random_headers += random.sample(optional_headers, ikeep)
    random_headers = list(set(random_headers))  # remove duplicates
    if len(random_headers) > hard_limit:
        # print(f"\tWARNING: Number of headers for node '{node}' is greater than hard limit ({hard_limit}).\n\tKeeping only the first {hard_limit} headers.")
        random_headers = random.sample(
            [h for h in random_headers if ".id" not in h],
            hard_limit - len([h for h in random_headers if h.endswith(".id")]),
        ) + [h for h in random_headers if h.endswith(".id")]
    return random_headers


# randomize_headers(node,dm,keep_min=0,keep_max=100,hard_limit=20,keep_required=True)


def order_nodes(nodes, dd):
    """This function takes a list of nodes and orders them by submission order.
    # test run parameters:
    # order_nodes(parents,dd,root_node=root_node)
    #
    """
    suborder = get_submission_order(dd)
    ordered_nodes = sorted(nodes, key=lambda x: suborder[x])
    return ordered_nodes


def get_node_paths(dm, nodes=None):
    """This function takes a data dictionary and finds all parent nodes up to the root node for each leaf node in the dictionary (default) or for the list of nodes provided.
    Returns a dictionary of nodes as keys and their paths to the root node as values.
    """
    paths = {}
    for node in nodes:  # node = nodes[0]
        parents = get_node_parents(node, dm)
        paths[node] = order_nodes(parents, dm)
    return paths


# get_node_paths(dm,leaf_nodes)


def randomly_group_nodes(nodes, node_limit=6, node_min=1):
    """
    This function takes a list of nodes (leaf nodes) and randomly selects a number of nodes between node_min and node_limit.
    This is to mimic data contributions that won't include all leaf nodes in the data model, but a subset.
    Returns a list of node groups (list of lists of nodes).
    """
    node_groups = []
    node_pool = copy.deepcopy(nodes)
    while len(node_pool) > 0:
        n = random.randint(node_min, node_limit)
        if n > len(node_pool):
            n = len(node_pool)
        nodes = random.sample(node_pool, n)
        for node in nodes:
            node_pool.remove(node)
        node_groups.append(nodes)
    return node_groups


# randomly_group_nodes(nodes=leaf_nodes,node_limit=6,node_min=1)
# # sanity check
# node_groups = randomly_group_nodes(nodes=leaf_nodes,node_limit=6,node_min=1)
# all_nodes = [node for nodes in node_groups for node in nodes]
# sorted(all_nodes) == sorted(leaf_nodes) # True :)


def validate_headers(gheaders, all_headers):
    # Check that each header in gheaders is in at least one node's all_headers
    for node in gheaders:
        headers = gheaders[node]
        # if len(headers) < 3 and node not in no_prop_nodes:
        #     sys.exit(f"\n\n\nHeaders in gheaders node '{node}' are less than 3!\ndd properties\n\t{list(dd[node]['properties'])}\n\nHeaders in gheaders\n\t{headers}")
        for header in headers:
            if (
                header
                not in [
                    item for sublist in list(all_headers.values()) for item in sublist
                ]
                and header != "project_id"
                and header != f"{node}_id"
            ):
                sys.exit(
                    f"\n\n\nHeader '{header}' in '{node}' not found in all_headers!"
                )

    # Check that each header in all_headers is in at least one node's gheaders (group headers)
    for node in all_headers:
        headers = all_headers[node]
        for header in all_headers[node]:
            # if header not in [item for sublist in list(gheaders.values()) for item in sublist] and ".id" not in header:
            if header not in [
                item for sublist in list(gheaders.values()) for item in sublist
            ]:
                sys.exit(f"\n\n\nHeader '{header}' in '{node}' not found in gheaders!")
    return True


def write_json(data, outfile):
    with open(outfile, "w") as f:
        json.dump(data, f, indent=4)
    # print(f"\tData model written to {outfile}")


def write_headers_to_files(headers, dm, out_dir="data_file_manifests"):
    """This function writes out the flattened file manifests for each node in a dictionary of node headers."""
    # print(f"Writing data file manifests to {out_dir}:")
    file_nodes = get_file_nodes(dm, use_file_name=True)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for node in headers:
        node_headers = headers[node]
        df = pd.DataFrame(columns=node_headers)
        if node in file_nodes:
            filename = f"{out_dir}/{node}_file_manifest.tsv"
        else:
            filename = f"{out_dir}/{node}_metadata.tsv"
        # print(f"\tWriting: {filename}")
        df.to_csv(filename, sep="\t", index=False)


# def remove_node_from_dm(node,dm):
#     """ This function takes a list of nodes and removes them from the data dictionary.
#         Removes the node and links to nodes in remaining nodes).
#     """
#     return dm


def write_node_group_schema(
    all_headers, dm, schema_name, groupname, groupdir, write_file=True
):
    """This function takes a dictionary of node headers and writes out the simplified data model schema for the group.
    Nodes in the group are lifted from the original schema with the headers replaced by the randomized headers.
    """
    # print(f"Writing node group schema to {groupdir}/{groupname}__simplified_dd.json")
    gdm = {"nodes": []}
    for node in all_headers:  # node = list(all_headers)[0]
        node_def = copy.deepcopy(get_node_def(node, dm))
        node_def["properties"] = [
            p for p in node_def["properties"] if p["name"] in all_headers[node]
        ]
        node_def["required"] = [
            p for p in node_def["required"] if p in all_headers[node]
        ]
        node_def["links"] = [l for l in node_def["links"] if l in all_headers]
        gdm["nodes"].append(node_def)
    if write_file:
        # file_name = f"{groupdir}/{groupname}__simplified_dd.json"
        file_name = f"{groupdir}/{schema_name}__{groupname}__jsonschema_dd.json"
        write_json(gdm, file_name)
    return gdm
