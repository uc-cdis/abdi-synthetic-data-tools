import os
import shutil
import json
import copy
import random
import datetime
from pathlib import Path


def read_schema(schema):
    """Reads in the input schema.json file for a Gen3 data dictionary and returns a Python dictionary."""
    with open(schema) as json_file:
        try:
            dm = json.load(json_file)
        except Exception as e:
            print(f"Error reading schema file: {schema}: \n\t{e}")
            return {}
    return dm


# schema = '/Users/christopher/Documents/Notes/AI/AI_data_curation/input_schemas/gen3_schemas/simplified_gen3_schemas/gen3.biodatacatalyst.nhlbi.nih.gov__jsonschema_dd.json'
# dm = read_schema(input_schema)


def read_schemas(schemas, exclude_nodes=None, exclude_props=None):
    """Given a list of Gen3 data dictionary schema files, return a dictionary of the schemas.
    Arguments:
        schemas(list): list of file paths to Gen3 data model schema.json files.
            Schema filenames must end in 'schema.json', e.g., 'bdc_schema.json'.
    """
    if exclude_nodes == None:
        exclude_nodes = [
            "program",
            "core_metadata_collection",
            "root",
            "metaschema",
            "data_release",
            "_settings",
            "_terms",
            "_definitions",
        ]
    if exclude_props == None:
        exclude_props = [
            "associated_ids",
            "authz",
            "callset",
            "case_ids",
            "case_submitter_id",
            "created_datetime",
            "error_type",
            "file_state",
            "ga4gh_drs_uri",
            "id",
            "project_id",
            "state",
            "state_comment",
            "subject_ids",
            "submitter_id",
            "token_record_id",
            "type",
            "updated_datetime",
        ]
    dms = {}
    node_counts = []
    prop_counts = []
    for schema in schemas:
        dm = read_schema(schema)
        node_defs = [n for n in dm["nodes"] if n not in exclude_nodes]
        node_counts.append(len(node_defs))
        props_count = []
        for node_def in node_defs:
            props = [p for p in node_def["properties"] if p not in exclude_props]
            props_count.append(len(props))
        average_prop_count = sum(props_count) / len(node_defs)
        prop_counts.append(
            average_prop_count
        )  # average number of properties per node per schema
        schema_name = schema.split("/")[-1].split("_")[0]
        print(
            f"\t{schema_name}: {len(node_defs)} nodes with ~{int(average_prop_count)} properties per node."
        )
        dms[schema_name] = dm
    print(
        f"Average node count per schema: {sum(node_counts)/len(node_counts)}, average number of properties per node: {int(sum(prop_counts)/len(prop_counts))}."
    )
    return dms


# gen3_dir = "/Users/christopher/Documents/Notes/AI/AI_data_curation/input_schemas/gen3_schemas/simplified_gen3_schemas"
# gen3_schemas = [f"{gen3_dir}/{f}" for f in os.listdir(gen3_dir) if f.endswith('__jsonschema_dd.json')]
# dms = read_schemas(gen3_schemas) # average node count for the 20 real Gen3 dds  = 35.25


def get_node_dms(node, dms):
    """This function takes a node name and a dictionary of data models and returns a dictionary of data models that contain the node."""
    node_dms = {}
    for dm_name in list(dms.keys()):
        if node in [n["name"] for n in dms[dm_name]["nodes"]]:
            node_dms[dm_name] = dms[dm_name]
    return node_dms


def get_node_defs(node, dms):
    """This function takes a node name and a dictionary of data models and returns a list of node definitions for that node."""
    node_defs = []
    for dm_name in list(dms.keys()):
        if node in [n["name"] for n in dms[dm_name]["nodes"]]:
            node_def = [n for n in dms[dm_name]["nodes"] if n["name"] == node][0]
            node_defs.append(node_def)
    return node_defs


def create_master_project(dms):
    """
    This function creates a master project node for a synthetic data model from all the input data models project nodes.
    It will include all properties from all project nodes in the input data models.
    """
    pdefs = get_node_defs("project", dms)
    ## get the unique set of properties across all project nodes
    project_props = []
    prop_names = sorted(
        list(
            set(
                [
                    p["name"]
                    for p in [
                        item
                        for sublist in [pdef["properties"] for pdef in pdefs]
                        for item in sublist
                    ]
                ]
            )
        )
    )
    for prop in prop_names:  # prop = prop_names[0]
        prop_nodes = [
            pdef for pdef in pdefs if prop in [p["name"] for p in pdef["properties"]]
        ]
        # select a random property definition from the list of property definitions
        prop_node = random.sample(prop_nodes, 1)[0]
        prop_def = [p for p in prop_node["properties"] if p["name"] == prop][0]
        project_props.append(
            prop_def
        )  # add the property definition to the master project def
    # get to required properties from each project node
    all_required = sorted(
        list(
            set(
                [
                    item
                    for sublist in [p["required"] for p in pdefs]
                    for item in sublist
                    if item in prop_names
                ]
            )
        )
    )
    # get random project description from the list of project nodes
    project_descs = [pdef["description"] for pdef in pdefs]
    project_desc = random.sample(project_descs, 1)[0]

    proj_def = {
        "name": "project",
        "description": project_desc,
        "links": [],
        "required": all_required,
        "properties": project_props,
    }
    return proj_def


# proj_def = create_master_project(dms)


def get_node_set(dms, sdm):
    sdm_nodes = [n["name"] for n in sdm["nodes"]]
    node_set = set()
    for dm in list(dms.values()):
        for node_name in [n["name"] for n in dm["nodes"] if n["name"] not in sdm_nodes]:
            node_set.add(node_name)
    return node_set


# node_set = get_node_set(dms,{'nodes':[]})


def get_prop_set(dms):
    """This function takes a list of simplified data models and returns a set of all properties across all nodes in the models."""
    prop_set = set()
    for dm in list(dms.values()):  # dm = list(dms.values())[0]
        for node_def in dm["nodes"]:
            node = node_def["name"]
            if "properties" in node_def:
                prop_names = [p["name"] for p in node_def["properties"]]
                for prop in prop_names:  # prop = props[0]
                    node_prop = f"{node}.{prop}"
                    prop_set.add(node_prop)
    return sorted(prop_set)


# all_props = get_prop_set(dms) # 9715


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


def get_submission_order(dm):
    """
    This function takes a data model, and then it determines the hierarchical order of nodes by looking at the links, which is the necessary Gen3 Sheepdog submission order.
    Returns a dictionary with the submission order of all nodes up to project.
    This particular version of the function excludes the program and core_metadata_collection nodes as well as the "system nodes".

    set(nodes).difference(set(suborder))
    """
    nodes = list_nodes(dm)
    suborder = {"project": 0}
    round = 0
    while len(suborder) < len(nodes):  # "root_node" != in "nodes", thus the +1
        round += 1
        # print("\nFinding submission order, round: {}".format(round))
        for node in nodes:  # node = nodes[1]
            # print(node)
            # if (len([item for item in suborder if node in item]) == 0):  # if the node is not in suborder
            if node not in suborder:
                # print(node)
                targets = list(get_node_links(node, dm))
                # Check if each linking node target is in submission order already, in which case we will add current node
                if False in [i in suborder for i in targets]:
                    # print("\t\tSkipping Node ({}): {}".format(round,node))
                    continue  # if any parent is not already in suborder, skip this node for now
                else:  # if all parents are already in suborder, add this node after the last parent to submit
                    # print("\t\tAdding Node ({}): {}".format(round,node))
                    parents_order = [
                        item for item in suborder if item in targets
                    ]  # get existing order for each parent in list
                    suborder[node] = (
                        max([suborder[parent] for parent in parents_order]) + 1
                    )  # add the node with the max order of the parents + 1
    sorted_suborder = dict(sorted(suborder.items(), key=lambda item: item[1]))
    return sorted_suborder


# get_submission_order(dm)
# get_node_def('aliquot',odm)['links']
# get_node_def('aliquot',dm)['links']


def order_nodes(nodes, dm):
    """This function takes a list of nodes and orders them by submission order.
    # test run parameters:
    # exclude_nodes = ['program', '_definitions', '_settings', '_terms', 'root', 'data_release', 'metaschema']
    # order_nodes(parents,dd,root_node=root_node,exclude_nodes=exclude_nodes)
    #
    """
    suborder = get_submission_order(dm)
    ordered_nodes = sorted(nodes, key=lambda x: suborder[x])
    return ordered_nodes


def order_sdm(sdm):
    """This function takes a simplified data model and returns it ordered by submission order"""
    suborder = get_submission_order(sdm)
    sdm["nodes"] = sorted(sdm["nodes"], key=lambda x: suborder[x["name"]])
    return sdm


def get_node_parents(node, dm):
    """This function takes a node and a Gen3 data model and finds all parent nodes up to project."""
    parents = []
    links = get_node_links(node, dm)
    for target in links:  # target = links[0]
        parents.append(target)
        pparents = get_node_parents(target, dm)
        parents += pparents
    # create a dictionary of parents where the keys are sorted using the order_nodes function
    ordered_parents = [
        n for n in sorted(list(set(parents)), key=lambda x: get_submission_order(dm)[x])
    ]
    return ordered_parents


# get_node_parents(node,dm)


def get_node_parents(node, dm):
    """This function takes a node and a Gen3 data model and finds all parent nodes up to project."""
    parents = []
    links = get_node_links(node, dm)
    for target in links:  # target = list(links)[0]
        parents.append(target)
        pparents = get_node_parents(target, dm)
        parents += pparents
    return list(set(parents))


# get_node_parents(node,dm)


def get_random_path(node, dm):
    """This function takes a node and a Gen3 data model and finds all parent nodes up to project but choosing randomly from the links each step up to project."""
    parents = []
    links = get_node_links(node, dm)
    random_links = random.sample(links, random.randint(1, len(links)))
    for target in random_links:  # target = list(links)[0]
        parents.append(target)
        pparents = get_node_parents(target, dm)
        parents += pparents
    ordered_parents = [
        n for n in sorted(list(set(parents)), key=lambda x: get_submission_order(dm)[x])
    ]
    return ordered_parents


# get_random_path(node,dm)


def list_nodes(sdm):
    """
    returns the list node names for a simplified data mode
    """
    nodes = [n["name"] for n in sdm["nodes"]]
    return nodes


def list_props(node, sdm):
    """
    returns the list node names for a simplified data mode
    """
    node_def = [n for n in sdm["nodes"] if n["name"] == node][0]
    props = [p["name"] for p in node_def["properties"]]
    return props


def get_sdm_synonyms(sdm, synonymous_nodes=None):
    """This function takes a synthetic data model and returns a dictionary of synonyms existing in the model."""
    if synonymous_nodes is None:
        synonymous_nodes = [
            ["study", "dataset", "clinical_trial", "collection", "research"],
            ["subject", "patient", "case", "participant"],
            ["biospecimen", "specimen"],
        ]
    nodes = list_nodes(sdm)
    sdm_synonyms = []
    for synonym_list in synonymous_nodes:
        synonyms = [n for n in nodes if n in synonym_list]
        if len(synonyms) > 1:
            sdm_synonyms.append(synonyms)
    return sdm_synonyms


# get_sdm_synonyms(sdm)


def update_sdm_synonyms(sdm, syn_lists):
    """This function takes a synthetic data model and a list of synonyms and merges the synonyms into one chosen node in the model."""
    udm = copy.deepcopy(sdm)
    if len(syn_lists) > 0:
        for syn_list in syn_lists:  # syn_list = syn_lists[0]
            chosen_name = random.sample(syn_list, 1)[0]  # subject
            chosen_node = [n for n in udm["nodes"] if n["name"] == chosen_name][0]
            syns = [i for i in syn_list if i != chosen_name]  # [case]
            # print("\tMerging synonyms: {} into chosen node: {}".format(syns,chosen_name))
            # merge syn props and links into chosen node
            for syn in syns:  # syn = syns[0] # case
                syn_node = [n for n in udm["nodes"] if n["name"] == syn][0]
                syn_props = [
                    p for p in syn_node["properties"] if p["name"] != f"{syn}.id"
                ]
                syn_links = syn_node["links"]
                for link in syn_links:  # link=syn_links[0]
                    link_prop = link + ".id"
                    if link_prop in [p["name"] for p in syn_props]:
                        p = [p for p in syn_props if p["name"] == link_prop][0]
                        if "description" in p:
                            p["description"] = p["description"].replace(
                                syn, chosen_name
                            )
                chosen_node["properties"] += [
                    p
                    for p in syn_props
                    if p["name"] not in [c["name"] for c in chosen_node["properties"]]
                ]
                chosen_node["links"] = list(
                    set(chosen_node["links"] + syn_node["links"])
                )
                # replace the syn with chosen_name in any 'links', 'required' and 'properties' for each other node
                for node_def in [
                    n
                    for n in udm["nodes"]
                    if n["name"] != chosen_name
                    and n["name"] != syn
                    and n["name"] != "project"
                ]:
                    for i in range(0, len(node_def["links"])):
                        if node_def["links"][i] == syn:
                            node_def["links"][i] = chosen_name
                    for i in range(0, len(node_def["required"])):
                        if node_def["required"][i] == f"{syn}.id":
                            node_def["required"][i] = f"{chosen_name}.id"
                    for i in range(0, len(node_def["properties"])):
                        if node_def["properties"][i]["name"] == f"{syn}.id":
                            node_def["properties"][i]["name"] = f"{chosen_name}.id"
                            node_def["properties"][i]["description"] = node_def[
                                "properties"
                            ][i]["description"].replace(syn, chosen_name)
                udm["nodes"] = [n for n in udm["nodes"] if n["name"] != syn]
                # udm_nodes = [n['name'] for n in udm['nodes']]  #check nodes in sdm
    return udm


# odm = copy.deepcopy(sdm)
# syn_lists = get_sdm_synonyms(sdm)
# udm = update_sdm_synonyms(sdm,syn_lists)
# udm_nodes = [n['name'] for n in udm['nodes']]  #check nodes in sdm


def get_all_links(sdm):
    """
    This function takes a synthetic data model and returns a list of all links in the model.
    """
    all_links = []
    for node_def in sdm["nodes"]:
        links = node_def["links"]
        all_links += links
        print(f"\t\tNode: {node_def['name']} has links: {links}")
    return list(set(all_links))


# all_links = get_all_links(sdm)


def fix_links(sdm):
    """This function takes a synthetic data model and checks that all links for each node exist in the model."""
    sdm_nodes = list_nodes(sdm)
    all_links = list(set([l for n in sdm["nodes"] for l in n["links"]]))
    remove_links = [l for l in all_links if l not in sdm_nodes]
    for node in sdm_nodes:  # node = sdm_nodes[0]
        node_def = [n for n in sdm["nodes"] if n["name"] == node][0]
        # print(f"\t\tNode: {node} has links: {node_def['links']}")
        node_def["links"] = [l for l in node_def["links"] if l not in remove_links]
        node_def["properties"] = [
            p
            for p in node_def["properties"]
            if p["name"].replace(".id", "") not in remove_links
        ]
        node_def["required"] = [
            r for r in node_def["required"] if r.replace(".id", "") not in remove_links
        ]
        if len(node_def["links"]) == 1:
            node_def["required"] = list(
                set(node_def["required"] + [node_def["links"][0] + ".id"])
            )
    return sdm


# sdm = copy.deepcopy(odm)
# fix_links(sdm)


# The script then randomly selects optional properties for each node in the synthetic data model.
def select_optional_properties(
    sdm, min_props_perc, max_props_perc, keep_required=False
):
    """
    Select random number of optional properties to add to the synthetic data model.
    """
    udm = copy.deepcopy(sdm)
    for node_def in [n for n in udm["nodes"]]:
        if "required" in node_def and keep_required:
            required_props = node_def["required"]
            keep_props = [
                p["name"]
                for p in node_def["properties"]
                if p["name"].endswith(".id") or p["name"] in required_props
            ]
        else:
            keep_props = [
                p["name"] for p in node_def["properties"] if p["name"].endswith(".id")
            ]
        optional_props = [
            p["name"] for p in node_def["properties"] if p["name"] not in keep_props
        ]
        if (
            len(optional_props) > 0
        ):  # get random integer of optional properties to keep between min and max percentages
            min_props = int(len(optional_props) * min_props_perc / 100)
            max_props = int(len(optional_props) * max_props_perc / 100)
            num_props = random.randint(min_props, max_props)
            keep_optional = random.sample(
                optional_props, num_props
            )  # randomly select optional properties to keep
            all_keep = keep_optional + keep_props
        else:
            all_keep = keep_props
        updated_props = (
            []
        )  # update node_def['properties'] making sure property names in node_def['properties'] are all unique
        for prop in node_def["properties"]:
            if prop["name"] in all_keep and prop["name"] not in [
                p["name"] for p in updated_props
            ]:
                updated_props.append(prop)
        node_def["properties"] = updated_props
    return udm


# sdm = select_optional_properties(sdm)


def truncate_sdm_descriptions(
    sdm, desc_limit=1000, log_file="description_truncation_log.json"
):
    """
    This function truncates description strings in simplified data models to a specified length.
    A small number of properties are hard-coded.
    """
    truncs = {}
    for node_def in sdm["nodes"]:
        if "description" in node_def:
            node_desc = node_def["description"]
            if len(node_desc) > desc_limit:
                if "." in desc:
                    tdesc = desc.split(".")[0] + "."
                elif ";" in desc:
                    tdesc = desc.split(";")[0] + "."
                else:
                    tdesc = desc[:desc_limit]
                print(
                    f"\tTruncating description from {len(desc)} to {len(tdesc)} characters."
                )
                node_def["description"] = tdesc
                truncs[node_def["name"]] = tdesc
        if "properties" in node_def:
            for prop_def in node_def["properties"]:
                if "description" in prop_def:
                    desc = prop_def["description"]
                    if (
                        '"Site where the subject was recruted. ARIC_A=field center A representing one of four anonymized centers (Forsyth County, NC, USA; Jackson, MS, USA; the northwest suburbs of Minneapolis, MN, USA; and Washington County, MD, USA) where baseline exam was conducted for ARIC (Atherosclerosis Risk in Communities), ARIC_B=field center B representing one of four anonymized centers (Forsyth County, NC, USA; Jackson, MS, USA; the northwest suburbs of Minneapolis, MN, USA; and Washington County, MD, USA) where baseline exam was conducted for ARIC (Atherosclerosis Risk in Communities), ARIC_C=field center C representing one of four anonymized centers (Forsyth County, NC, USA; Jackson, MS, USA; the northwest suburbs of Minneapolis, MN, USA; and Washington County, MD, USA) where baseline exam was conducted for ARIC (Atherosclerosis Risk in Communities), ARIC_D=field center D representing one of four anonymized centers (Forsyth County, NC, USA; Jackson, MS, USA; the northwest suburbs of Minneapolis, MN, USA; and Washington County, MD, USA) where baseline exam was conducted for ARIC (Atherosclerosis Risk in Communities), CARDIA_1=field center 1 representing one of four anonymized field centers (University of Alabama, Birmingham, AL, USA; Northwestern University, IL, USA; University of Minnesota, MN, USA; Kaiser Foundation Research Institute, Oakland, CA, USA) for subjects in the CARE project within CARDIA (Coronary Artery Risk Development in Young Adults), CARDIA_2=field center 2 representing one of four anonymized field centers (University of Alabama, Birmingham, AL, USA; Northwestern University, IL, USA; University of Minnesota, MN, USA; Kaiser Foundation Research Institute, Oakland, CA, USA) for subjects in the CARE project within CARDIA (Coronary Artery Risk Development in Young Adults), CARDIA_3=field center 3 representing one of four anonymized field centers (University of Alabama, Birmingham, AL, USA; Northwestern University, IL, USA; University of Minnesota, MN, USA; Kaiser Foundation Research Institute, Oakland, CA, USA) for subjects in the CARE project within CARDIA (Coronary Artery Risk Development in Young Adults), CARDIA_4=field center 4 representing one of four anonymized field centers (University of Alabama, Birmingham, AL, USA; Northwestern University, IL, USA; University of Minnesota, MN, USA; Kaiser Foundation Research Institute, Oakland, CA, USA) for subjects in the CARE project within CARDIA (Coronary Artery Risk Development in Young Adults), CHS_BOWMAN.GRAY=clinic at Bowman Gray University (Forsyth County, NC, USA) for CHS (Cardiovascular Health Study), CHS_DAVIS=clinic at Davis University (Sacramento County, CA, USA) for CHS (Cardiovascular Health Study), CHS_HOPKINS=clinic at Johns Hopkins University (Washington County, MD, USA) for CHS (Cardiovascular Health Study), CHS_PITT=clinic at University of Pittsburgh (Pittsburgh, PA, USA) for CHS (Cardiovascular Health Study), COPDGene_C01=clinical center C01 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C02=clinical center C02 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C03=clinical center C03 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C04=clinical center C04 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C05=clinical center C05 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C06=clinical center C06 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C07=clinical center C07 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C08=clinical center C08 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C09=clinical center C09 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C10=clinical center C10 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C11=clinical center C11 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C12=clinical center C12 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C13=clinical center C13 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C14=clinical center C14 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C15=clinical center C15 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C16=clinical center C16 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C17=clinical center C17 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C18=clinical center C18 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C19=clinical center C19 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C20=clinical center C20 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), COPDGene_C21=clinical center C21 representing one of 21 de-identified clinical centers for COPDGene (Genetic Epidemiology of COPD), GENOA_MN=recruitment from Rochester, MN, US, GENOA_MS=recruitment from Jackson, MS, US, GOLDN_MN=recruitment center at Minneapolis, MN, USA for GOLDN (Genetics of Lipid Lowering Drugs and Diet Network Lipodemics Study), GOLDN_UT=recruitment center at Salt Lake City, UT, USA for GOLDN (Genetics of Lipid Lowering Drugs and Diet Network Lipodemics Study), HCHS_SOL_Bronx=recruitment center Bronx, NY, USA for HCHS/SOL (Hispanic Community Health Study/Study of Latinos), HCHS_SOL_Chicago=recruitment center Chicago, IL, USA for HCHS/SOL (Hispanic Community Health Study/Study of Latinos), HCHS_SOL_Miami=recruitment center Miami, FL, USA for HCHS/SOL (Hispanic Community Health Study/Study of Latinos), HCHS_SOL_SanDiego=recruitment center San Diego, CA, USA for HCHS/SOL (Hispanic Community Health Study/Study of Latinos), JHS_Hinds=recruitment from urban and rural areas of Hinds county, MS, USA for JHS (Jackson Heart Study), JHS_Madison=recruitment from urban and rural areas of Madison county, MS, USA for JHS (Jackson Heart Study), JHS_Rankin=recruitment from urban and rural areas of Rankin county, MS, USA for JHS (Jackson Heart Study), JHS_Unknown=recruitment from unknown county in MS, USA for JHS (Jackson Heart Study), Mayo_VTE_Midwest_US=state of residence (at time of enrollment for Mayo_VTE study) is in the South region of the USA as defined by the Census Bureau, Mayo_VTE_Northeast_US=state of residence (at time of enrollment for Mayo_VTE study) is in the Northeast region of the USA as defined by the Census Bureau, Mayo_VTE_non_US=state of residence (at time of enrollment for Mayo_VTE study) is from a country outside the USA, Mayo_VTE_South_US=state of residence (at time of enrollment for Mayo_VTE study) is in the Midwest region of the USA as defined by the Census Bureau, Mayo_VTE_West_US=state of residence (at time of enrollment for Mayo_VTE study) is in the West region of the USA as defined by the Census Bureau, MESA_COL=field center/baseline clinic at Columbia University, NY, USA for MESA (Multi-Ethnic Study of Atherosclerosis Cohort), MESA_JHU=field center/baseline clinic at Johns Hopkins University, MD, USA for MESA (Multi-Ethnic Study of Atherosclerosis Cohort), MESA_NWU=field center/baseline clinic at Northwestern University, IL, USA for MESA (Multi-Ethnic Study of Atherosclerosis Cohort), MESA_UCLA=field center/baseline clinic at University of California, Los Angeles, CA, USA for MESA (Multi-Ethnic Study of Atherosclerosis Cohort), MESA_UMN=field center/baseline clinic at University of Minnesota, MN, USA for MESA (Multi-Ethnic Study of Atherosclerosis Cohort), MESA_WFU=field center/baseline clinic at Wake Forest University, NC, USA for MESA (Multi-Ethnic Study of Atherosclerosis Cohort), SAS_Apia.urban=recruitment census region of Apia Urban Area in Samoa for SAS (Genome-wide Association Study of Adiposity in Samoans), SAS_NW.Upola=recruitment census region of Northwest Upola in Samoa for SAS (Genome-wide Association Study of Adiposity in Samoans), SAS_rest.Upola=recruitment census region including rest of Upola in Samoa for SAS (Genome-wide Association Study of Adiposity in Samoans), SAS_Savaii=recruitment census region of Savaii in Samoa for SAS (Genome-wide Association Study of Adiposity in Samoans), WHI_Midwest=recruitment from Midwest region of the USA for WHI (Womens Health Initiative), WHI_Northeast=recruitment from Northeast region of the USA for WHI (Womens Health Initiative), WHI_South=recruitment from South region of the USA for WHI (Womens Health Initiative), WHI_West=recruitment from West region of the USA for WHI (Womens Health Initiative)"'
                        in desc
                    ):
                        desc = "Site where the subject was recruited, corresponding to anonymized field centers from various epidemiological studies, including ARIC, CARDIA, CHS, COPDGene, GENOA, GOLDN, HCHS/SOL, JHS, Mayo_VTE, MESA, SAS, and WHI. Sites represent specific universities, cities, or regions across the U.S. and Samoa, with identifiers linked to their respective studies while maintaining participant confidentiality."
                    elif (
                        "CHB Han Chinese in Beijing, China EAS; JPT Japanese in Tokyo, Japan EAS; CHS Southern Han Chinese EAS; CDX Chinese Dai in Xishuangbanna, China EAS; KHV Kinh in Ho Chi Minh City, Vietnam EAS; CEU Utah Residents (CEPH) with Northern and Western European Ancestry EUR; TSI Toscani in Italia EUR; FIN Finnish in Finland EUR; GBR British in England and Scotland EUR; IBS Iberian Population in Spain EUR; YRI Yoruba in Ibadan, Nigeria AFR; LWK Luhya in Webuye, Kenya AFR; GWD Gambian in Western Divisions in the Gambia AFR; MSL Mende in Sierra Leone AFR; ESN Esan in Nigeria AFR; ASW Americans of African Ancestry in SW USA AFR; ACB African Caribbeans in Barbados AFR; MXL Mexican Ancestry from Los Angeles USA AMR; PUR Puerto Ricans from Puerto Rico AMR; CLM Colombians from Medellin, Colombia AMR; PEL Peruvians from Lima, Peru AMR; GIH Gujarati Indian from Houston, Texas SAS; PJL Punjabi from Lahore, Pakistan SAS; BEB Bengali from Bangladesh SAS; STU Sri Lankan Tamil from the UK SAS; ITU Indian Telugu from the UK"
                        in desc
                    ):
                        desc = "Population group of the subject based on geographic and ancestral origin. Categories include East Asian (EAS), European (EUR), African (AFR), American (AMR), and South Asian (SAS) populations, with specific subgroups from China, Japan, Vietnam, Europe, Africa, the Americas, and South Asia. Identifiers represent regional or ethnic ancestry, maintaining study relevance and classification."
                    elif (
                        "It is possible that some records destined for the Observation table have two clinical ideas represented in one source code. This is common with ICD10 codes that describe a family history of some Condition, for example. In OMOP the Vocabulary breaks these two clinical ideas into two codes; one becomes the OBSERVATION_CONCEPT_ID and the other becomes the VALUE_AS_CONCEPT_ID. It is important when using the Observation table to keep this possibility in mind and to examine the VALUE_AS_CONCEPT_ID field for relevant information. Note that the value of VALUE_AS_CONCEPT_ID may be provided through mapping from a source Concept which contains the content of the Observation. In those situations, the CONCEPT_RELATIONSHIP table in addition to the 'Maps to' record contains a second record with the relationship_id set to 'Maps to value'. For example, ICD10 Z82.4 'Family history of ischaemic heart disease and other diseases of the circulatory system' has a 'Maps to' relationship to 4167217 'Family history of clinical finding' as well as a 'Maps to value' record to 134057 'Disorder of cardiovascular system'. If there's no categorial result in a source_data, set value_as_concept_id to NULL, if there is a categorial result in a source_data but without mapping, set value_as_concept_id to 0."
                        in desc
                    ):
                        desc = "Some Observation records contain multiple clinical ideas in one source code, common in ICD10 (e.g., family history codes). OMOP separates these into OBSERVATION_CONCEPT_ID and VALUE_AS_CONCEPT_ID. VALUE_AS_CONCEPT_ID may be mapped from a source Concept using 'Maps to value' in the CONCEPT_RELATIONSHIP table. If no categorical result exists, set it to NULL; if unmapped, set it to 0. Always check this field for relevant information."
                    desc = desc.strip('"')
                    if len(desc) > desc_limit:
                        if "." in desc:
                            tdesc = desc.split(".")[0] + "."
                        elif ";" in desc:
                            tdesc = desc.split(";")[0] + "."
                        else:
                            tdesc = desc[:desc_limit]
                        print(
                            f"\tTruncating description from {len(desc)} to {len(tdesc)} characters."
                        )
                        prop_def["description"] = tdesc
                        truncs[prop_def["name"]] = tdesc
    if len(truncs) > 0:
        # print(f"\tTruncated description from {len(desc)} to {len(tdesc)} characters.")
        # append the truncated desc and original desc to a log file
        with open(log_file, "a") as f:
            json.dump(truncs, f, indent=4)
    return sdm


# sdm = truncate_sdm_descriptions(sdm,desc_limit=1000,log_file="description_truncation_log.json")
