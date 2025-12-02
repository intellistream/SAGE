// GTI
// Created by Ruiyao Ma on 24-02-22

#include "gti.h"

// Comparison function for two entries with dis_p
bool compareEnDisp(GTI_Entry *e1, GTI_Entry *e2)
{
    return e1->dis_p < e2->dis_p;
}

// Comparison function for two entries with dis_p + radius
bool compareEnDispR(GTI_Entry *e1, GTI_Entry *e2)
{
    return (e1->dis_p + e1->radius) < (e2->dis_p + e2->radius);
}

// Build GTI
void GTI::buildGTI(unsigned capacity_up_i, unsigned capacity_up_l, int m, Objects *data)
{
    init(capacity_up_i, capacity_up_l, m, data); // Initialize GTI
    insertAll();                                 // Insert all objects to tree
    buildGraphSec();                             // Build graph at second level
}

// Initialize GTI
void GTI::init(unsigned capacity_up_i, unsigned capacity_up_l, int m, Objects *data)
{
    this->data = data; // Initialize data

//    this->data = new Objects();
//    this->data->dim = data->dim;
//    this->data->num = data->num;
//    this->data->type = data->type;
//
//    this->data->vecs.clear();
//    this->data->vecs.reserve(data->vecs.size());
//    for (const auto& vec : data->vecs) {
//        this->data->vecs.emplace_back(vec);
//    }
//    std::cout << "init data->dim = " << this->data->dim <<std::endl;
    // Initialize node capacity
    this->capacity_up_i = capacity_up_i;
    this->capacity_up_l = capacity_up_l;

    // Initialize root node
    root = new GTI_Node();
    root->entries.resize(0);
    root->parent_node = NULL;
    root->type = 1; // Initially, the root node is a leaf node
    root->level = 0;

    height = 1; // Initialize tree height

    // Initialize graph parameters
    this->m = m;
    int core_count = std::thread::hardware_concurrency(); // Get number of cores
//    n_threads = core_count / 2;                           // Number of threads
    n_threads = 1;
    max_m0 = 2 * m;
    ef_construction = 5 * max_m0;
}

// Find parent node
GTI_Node *GTI::findParentNode(GTI_Node *N, GTI_Node *node)
{
    if (N == NULL || node == NULL)
        return NULL;

    if (N->type == 1)
        return NULL;

    for (unsigned i = 0; i < N->entries.size(); i++)
    {
        GTI_Node *child = N->entries[i]->child;
        if (child == node)
        {
            return N;
        }
        else
        {
            GTI_Node *parent = findParentNode(child, node);
            if (parent != NULL)
            {
                return parent;
            }
        }
    }

    return NULL;
}

// Find parent entry
int GTI::findParentEntry(GTI_Node *parent, GTI_Node *node)
{
    if (parent == NULL || node == NULL)
        return -1;

    for (unsigned i = 0; i < parent->entries.size(); i++)
    {
        if (parent->entries[i]->child == node)
            return i;
    }

    return -1;
}

// Find entry id in the node
int GTI::findEntry(GTI_Node *node, unsigned oid)
{
    if (node == NULL)
        return -1;

    for (unsigned i = 0; i < node->entries.size(); i++)
    {
        if (node->entries[i] != nullptr)
            if (node->entries[i]->oid == oid)
                return i;
    }

    return -1;
}

// Insert all objects to tree
void GTI::insertAll()
{
    std::vector<float> dists;         // Distances to routing objects
    std::vector<unsigned> entries_in; // 0, distance calculated and pruned; 1, distance calculated and not pruned (entries without radius enlargement);
                                      // 2, parent pruning

    // Insert all objects
    system("setterm -cursor on");
    for (unsigned i = 0; i < data->num; i++)
    {
        // Create leaf entry
        GTI_Entry *entry = new GTI_Entry();
        entry->oid = (int)i;
        entry->dis_p = INF_DIS;
        entry->radius = INF_DIS;
        entry->child = NULL;

//         Print progress bar;
//         if (i < data->num - 1)
//         {
//             printf("\rBUilding[%.2lf%%]:", i * 100.0 / (data->num - 1));
//         }
//         else
//         {
//             printf("\rDone[%.2lf%%]:", i * 100.0 / (data->num - 1));
//         }
//         int show_num = i * 20 / data->num;
//         for (int j = 1; j <= show_num; j++)
//         {
//             std::cout << "█";
//         }

        insert(root, entry, entries_in, dists, INF_DIS); // Insert objects
    }
    // std::cout << std::endl;
    // system("setterm -cursor on");

    std::vector<unsigned>().swap(entries_in);
    std::vector<float>().swap(dists);
}

// Insert objects
void GTI::insert(GTI_Node *node, GTI_Entry *entry, std::vector<unsigned> &entries_in, std::vector<float> &dists, float dis_p2o)
{
    if (node->type == 0) // Current node is an internal node
    {
        std::vector<unsigned>().swap(entries_in);
        std::vector<float>().swap(dists);
        entries_in.insert(entries_in.end(), node->entries.size(), 0);
        dists.resize(node->entries.size());

        bool is_entries_in = false; // false, no entry without radius enlargement
                                    // true, entries without radius enlargement
        float min_dis = INF_DIS;    // Min distance
        int min_id = 0;             // Entry ID corresponding to the min distance

        Distance *distance = new Distance();

        // Determination of entries_in
        for (unsigned i = 0; i < node->entries.size(); i++)
        {
            // Parent is not NULL
            if (node->parent_node != NULL)
            {
                // Use parent for pruning
                float dis = abs(dis_p2o - node->entries[i]->dis_p);
                if (dis > node->entries[i]->radius)
                {
                    entries_in[i] = 2; // The radius of the entry is increased
                }
            }

            // Not pruned by the parent
            if (entries_in[i] != 2)
            {
                float dis = distance->getDisP(data->vecs[node->entries[i]->oid].data(), data->vecs[entry->oid].data(),
                                              data->type, data->dim); // Calculate distance

                if (dis <= node->entries[i]->radius) // Distance calculated and not pruned (entries without radius enlargement)
                {
                    entries_in[i] = 1;
                    is_entries_in = true;

                    // Find the min distance
                    if (dis < min_dis)
                    {
                        min_dis = dis;
                        min_id = i;
                    }
                }
                dists[i] = dis;
            }
        }

        // No entry without radius enlargement
        if (!is_entries_in)
        {
            min_dis = INF_DIS;

            // Find the min distance (min radius increases)
            for (unsigned i = 0; i < node->entries.size(); i++)
            {
                if (entries_in[i] == 2)
                {
                    float dis = distance->getDisP(data->vecs[node->entries[i]->oid].data(), data->vecs[entry->oid].data(),
                                                  data->type, data->dim); // Calculate distance
                    dists[i] = dis;
                }

                // Find the min distance (min radius increases)
                if (dists[i] - node->entries[i]->radius < min_dis)
                {
                    min_dis = dists[i] - node->entries[i]->radius;
                    min_id = i;
                }
            }

            node->entries[min_id]->radius = dists[min_id]; // Update radius
        }

        delete distance;
        distance = NULL;

        insert(node->entries[min_id]->child, entry, entries_in, dists, dists[min_id]); // Recursive insertion
    }
    else // Current node is a leaf node
    {
        if (node->entries.size() < capacity_up_l) // Node is not full
        {
            // Record distance from parent
            if (node->parent_node != NULL)
            {
                entry->dis_p = dis_p2o;
            }

            node->entries.push_back(entry); // Store the enrty in leaf node
        }
        else // Node is full
        {
            auto s = std::chrono::high_resolution_clock::now();
            split(node, entry); // Split node
            auto e = std::chrono::high_resolution_clock::now();
            std::chrono::duration<float> diff = e - s;
            time_split += diff.count();
        }
    }
}

// Split node
void GTI::split(GTI_Node *node, GTI_Entry *entry)
{
    GTI_Node *node2 = new GTI_Node();
    GTI_Entry *entry1 = new GTI_Entry();
    GTI_Entry *entry2 = new GTI_Entry();
    std::vector<GTI_Entry *> entries;
    int min_oid[2]; // The index of the selected entry
    auto s = std::chrono::high_resolution_clock::now();
    GTI_Node *parent_node = node->parent_node; // Parent node
    auto e = std::chrono::high_resolution_clock::now();
    std::chrono::duration<float> diff = e - s;
    std::vector<float> dists_split;

    // Initialize split information
    for (unsigned i = 0; i < node->entries.size(); i++)
    {
        entries.push_back(node->entries[i]);
    }
    entries.push_back(entry);
    node2->type = node->type;
    node2->level = node->level;
    entry1->child = node;
    entry2->child = node2;

    // Promote and partition
    promoteLb(entries, min_oid, parent_node, node, dists_split);                            // mM_RAD2 methods to choose two new routing objects
    partitionGh(entries, node, node2, entry1, entry2, min_oid[0], min_oid[1], dists_split); // Divide the entries into two nodes using generalized hyperplane

    // Release memory
    std::vector<GTI_Entry *>().swap(entries);
    std::vector<float>().swap(dists_split);

    if (parent_node == NULL) // Current node is root node, allocate a new root node
    {
        // Allocate a new root node
        height++;
        GTI_Node *new_root = new GTI_Node();
        new_root->type = 0;
        new_root->parent_node = NULL;
        new_root->level = height;

        // Update information
        entry1->dis_p = INF_DIS;
        entry2->dis_p = INF_DIS;
        new_root->entries.push_back(entry1);
        new_root->entries.push_back(entry2);
        node->parent_node = new_root;
        node2->parent_node = new_root;
        root = new_root;
    }
    else // Current node is not root node
    {
        float dist = INF_DIS;
        GTI_Node *grand_node = parent_node->parent_node;          // Grand node
        int parent_entry_id = findParentEntry(parent_node, node); // Parent entry id

        // Calculate the distance to new entry1's parent
        if (grand_node != NULL)
        {
            int grand_entry_id = findParentEntry(grand_node, parent_node); // Grandpa entry id
            Distance *distance = new Distance();
            int rid = grand_node->entries[grand_entry_id]->oid;
            dist = distance->getDisP(data->vecs[entry1->oid].data(), data->vecs[rid].data(), data->type, data->dim);
            delete distance;
            distance = NULL;
        }
        entry1->dis_p = dist;

        // Replace old parent entry with new entry1
        delete parent_node->entries[parent_entry_id];
        parent_node->entries[parent_entry_id] = NULL;
        parent_node->entries[parent_entry_id] = entry1;

        if (parent_node->entries.size() < capacity_up_i) // Parent node is not full, store entry2
        {
            // Calculate the distance to new entry's parent
            float dist = INF_DIS;
            if (grand_node != NULL)
            {
                int grand_entry_id = findParentEntry(grand_node, parent_node); // Grandpa entry id
                Distance *distance = new Distance();
                int rid = grand_node->entries[grand_entry_id]->oid;
                dist = distance->getDisP(data->vecs[entry2->oid].data(), data->vecs[rid].data(), data->type, data->dim);
                delete distance;
                distance = NULL;
            }
            entry2->dis_p = dist;

            // Store entry2 in parent node
            parent_node->entries.push_back(entry2);
            node2->parent_node = parent_node;
        }
        else // Parent node is full, split nodes recursively
        {
            split(parent_node, entry2); // Split nodes recursively
        }
    }
}

// M_LB_DIST1 methods to choose two new routing objects
void GTI::promoteLb(std::vector<GTI_Entry *> &entries, int *min_oid, GTI_Node *parent_node, GTI_Node *node, std::vector<float> &dists_split)
{
    dists_split.resize(2 * entries.size()); // Distance between any pair
    Distance *distance = new Distance();
    int oid1 = 0;
    int oid2 = 0;

    if (parent_node != NULL) // Parent node is not null
    {
        // Confirm parent entry's routing object as the first routing object
        int parent_entry_id = findParentEntry(parent_node, node);
        oid1 = parent_node->entries[parent_entry_id]->oid;

        // Get the distance between the new entry and the first routing object
        for (unsigned i = 0; i < entries.size(); i++)
        {
            if (i < entries.size() - 1)
            {
                dists_split[i] = entries[i]->dis_p;
            }
            else
            {
                int oid = entries[i]->oid;
                float dist = distance->getDisP(data->vecs[oid1].data(), data->vecs[oid].data(),
                                               data->type, data->dim);
                dists_split[i] = dist;
            }
        }
    }
    else // Parent node is null
    {
        oid1 = entries[entries.size() - 2]->oid; // Confirm the first entry's routing objrct as the first routing object

        // Calculates the distances between all entries and the first routing object
        // #pragma omp parallel num_threads(48)
        for (unsigned i = 0; i < entries.size(); i++)
        {
            int oid = entries[i]->oid;
            float dist = distance->getDisP(data->vecs[oid1].data(), data->vecs[oid].data(),
                                           data->type, data->dim);
            dists_split[i] = dist;
        }
    }

    // Find the farthest entry from the first routing object as the second routing object
    auto max_it_entry = std::max_element(dists_split.begin(), dists_split.begin() + entries.size());
    int max_index_entry = std::distance(dists_split.begin(), max_it_entry);
    oid2 = entries[max_index_entry]->oid;

    // Store two routing objects
    min_oid[0] = oid1;
    min_oid[1] = oid2;

    // if (oid1 == oid2)
    //     printf("equal!!!\n");

    // Calculates the distances between all entries and the first routing object
    // #pragma omp parallel num_threads(48)
    for (unsigned i = 0; i < entries.size(); i++)
    {
        int oid = entries[i]->oid;
        float dist = distance->getDisP(data->vecs[oid2].data(), data->vecs[oid].data(),
                                       data->type, data->dim);
        dists_split[entries.size() + i] = dist;
    }

    delete distance;
    distance = NULL;
}

// Divide the entries into two nodes using generalized hyperplane
void GTI::partitionGh(std::vector<GTI_Entry *> &entries, GTI_Node *node1, GTI_Node *node2, GTI_Entry *entry1,
                      GTI_Entry *entry2, int oid1, int oid2, std::vector<float> dists_split)
{
    std::vector<int> node1_idx; // Original index of entry in node1
    std::vector<int> node2_idx; // Original index of entry in node2
    // std::vector<GTI_Entry *>().swap(node1->entries);
    // std::vector<GTI_Entry *>().swap(node2->entries);
    node1->entries.clear();
    node2->entries.clear();

    // Divide the entries into two nodes using generalized hyperplane partition
    for (unsigned i = 0; i < entries.size(); i++)
    {
        if (dists_split[i] < dists_split[entries.size() + i]) // Assigned to node1
        {
            entries[i]->dis_p = dists_split[i];
            node1->entries.push_back(entries[i]);
            node1_idx.push_back(i);
            if (entries[i]->child != NULL)
            {
                entries[i]->child->parent_node = node1;
            }
        }
        else // Assigned to node2
        {
            entries[i]->dis_p = dists_split[entries.size() + i];
            node2->entries.push_back(entries[i]);
            node2_idx.push_back(i);
            if (entries[i]->child != NULL)
                entries[i]->child->parent_node = node2;
        }
    }

    // Update radius of promote entries
    if (entries[0]->child == NULL) // Split leaf node
    {
        auto max_it_entry1 = std::max_element(node1->entries.begin(), node1->entries.end(), compareEnDisp);
        auto max_it_entry2 = std::max_element(node2->entries.begin(), node2->entries.end(), compareEnDisp);
        int max_index_entry1 = std::distance(node1->entries.begin(), max_it_entry1);
        int max_index_entry2 = std::distance(node2->entries.begin(), max_it_entry2);
        entry1->radius = node1->entries[max_index_entry1]->dis_p;
        entry2->radius = node2->entries[max_index_entry2]->dis_p;
    }
    else // Split internal node
    {
        auto max_it_entry1 = std::max_element(node1->entries.begin(), node1->entries.end(), compareEnDispR);
        auto max_it_entry2 = std::max_element(node2->entries.begin(), node2->entries.end(), compareEnDispR);
        int max_index_entry1 = std::distance(node1->entries.begin(), max_it_entry1);
        int max_index_entry2 = std::distance(node2->entries.begin(), max_it_entry2);
        entry1->radius = node1->entries[max_index_entry1]->dis_p + node1->entries[max_index_entry1]->radius;
        entry2->radius = node2->entries[max_index_entry2]->dis_p + node2->entries[max_index_entry2]->radius;
    }

    std::sort(node1->entries.begin(), node1->entries.end(), compareEnDisp);
    std::sort(node2->entries.begin(), node2->entries.end(), compareEnDisp);

    // Update other information of promote entries
    entry1->oid = oid1;
    entry2->oid = oid2;

    // Release memory
    std::vector<int>().swap(node1_idx);
    std::vector<int>().swap(node2_idx);
}

// Build graph at second level
void GTI::buildGraphSec()
{
    std::vector<GTI_Node *> nodes;
    nodes.push_back(root);
    map.resize(data->num);
    std::fill(map.begin(), map.end(), -1);

    // Build graph in second layer
    unsigned size = nodes.size();
    for (unsigned i = 0; i < height - 1; i++)
    {
        for (unsigned j = 0; j < size; ++j)
        {
            if (i < height - 2) // Upper level
            {
                for (unsigned k = 0; k < nodes[j]->entries.size(); k++)
                {
                    nodes.push_back(nodes[j]->entries[k]->child);
                }
            }
            else // Second level
            {
                // Get entries of second level
                for (unsigned k = 0; k < nodes[j]->entries.size(); k++)
                {
                    entries_sec.push_back(nodes[j]->entries[k]);
                    unsigned oid = nodes[j]->entries[k]->oid;
                    map[oid] = entries_sec.size() - 1;
                }
            }
        }
        nodes.erase(nodes.begin(), nodes.begin() + size);
        size = nodes.size();
    }

    // Build graph at second level
    index_hnsw = new n2::Hnsw(data->dim, "L2");
    for (unsigned i = 0; i < entries_sec.size(); i++)
    {
        unsigned oid = entries_sec[i]->oid;
        index_hnsw->AddData(data->vecs[oid]); // Add data
    }
    index_hnsw->Build(m, max_m0, ef_construction, n_threads); // Build graph
}

// Insert data into GTI
void GTI::insertGTI(Objects *insert_data)
{
    unsigned old_data_size = data->num;                        // Old data size
    unsigned new_data_size = old_data_size + insert_data->num; // New data size
    data->vecs.insert(data->vecs.end(), insert_data->vecs.begin(), insert_data->vecs.end());
    data->num = new_data_size;

    insertTree(old_data_size);  // Insert data into tree
    insertGraph(old_data_size); // Insert data into graph
}

// Insert data into tree
void GTI::insertTree(unsigned old_data_size)
{
    std::vector<float> dists;         // Distances to routing objects
    std::vector<unsigned> entries_in; // 0, distance calculated and pruned; 1, distance calculated and not pruned (entries without radius enlargement); 2, parent pruning
    for (unsigned i = old_data_size; i < data->num; i++)
    {
        // Create leaf entry
        GTI_Entry *entry = new GTI_Entry();
        entry->oid = (int)i;
        entry->dis_p = INF_DIS;
        entry->radius = INF_DIS;
        entry->child = NULL;

        insert(root, entry, entries_in, dists, INF_DIS); // Insert objects
    }
    std::vector<unsigned>().swap(entries_in);
    std::vector<float>().swap(dists);
}

// Insert data into graph
void GTI::insertGraph(unsigned old_data_size)
{
    index_hnsw->UnloadModel();
    std::vector<GTI_Node *> nodes;
    nodes.push_back(root);
    map.resize(data->num);
    std::fill(map.begin() + old_data_size, map.end(), -1);

    // Insert graph in second layer
    unsigned size = nodes.size();
    for (unsigned i = 0; i < height - 1; i++)
    {
        for (unsigned j = 0; j < size; ++j)
        {
            if (i < height - 2) // Upper level
            {
                for (unsigned k = 0; k < nodes[j]->entries.size(); k++)
                {
                    nodes.push_back(nodes[j]->entries[k]->child);
                }
            }
            else // Second level
            {
                // Update entries of second level
                for (unsigned k = 0; k < nodes[j]->entries.size(); k++)
                {
                    unsigned oid = nodes[j]->entries[k]->oid;
                    if (map[oid] == -1) // Insert data into graph
                    {
                        map[oid] = entries_sec.size();
                        entries_sec.push_back(nodes[j]->entries[k]);
                        index_hnsw->AddDataM(data->vecs[oid]); // Add data
                    }
                    else // Update the entry
                    {
                        int eid = map[oid];
                        entries_sec[eid] = nodes[j]->entries[k];
                    }
                }
            }
        }
        nodes.erase(nodes.begin(), nodes.begin() + size);
        size = nodes.size();
    }

    index_hnsw->buildFromInsert(); // Insert data into graph
}

// Delete data from GTI
void GTI::deleteGTI(Objects *delete_data)
{
    std::vector<unsigned> delete_oids;     // Ids of data needed to be deleted
    deleteTree(delete_data, delete_oids);  // Delete data from tree
    deleteGraph(delete_data, delete_oids); // Delete data from graph
}

// Delete data from tree
void GTI::deleteTree(Objects *delete_data, std::vector<unsigned> &delete_oids)
{
    std::vector<GTI_Node *> delete_nodes; // Nodes to delete
    std::vector<unsigned> delete_eids;    // Ids of leaf entries to delete

// Find delete data
#pragma omp parallel for
    for (unsigned i = 0; i < delete_data->num; i++)
    {
        GTI_Node *leaf_node; // Leaf node
        unsigned leaf_eid;   // Id of leaf entry
        std::vector<Neighbor> result;
        search(delete_data->vecs[i].data(), 51, 1, result); // 1-NN search using graph

        bool is_same = true;
        for (unsigned j = 0; j < data->dim; j++)
        {
            if (delete_data->vecs[i][j] != data->vecs[result[0].id][j])
            {
                is_same = false;
                break;
            }
        }

        if (is_same) // Find data using graph
        {
            leaf_node = entries_sec[result[0].nid]->child;
            leaf_eid = result[0].oid;
        }
        else // Do not find data using graph; then range search using tree
        {
            findLeaf(delete_data->vecs[i].data(), leaf_node, leaf_eid); // Find the leaf of the data
        }
        unsigned temp_oid = leaf_node->entries[leaf_eid]->oid;
        GTI_Node *temp_node = leaf_node;
        unsigned temp_eid = leaf_eid;

#pragma omp critical
        {
            delete_oids.push_back(temp_oid);
            delete_nodes.push_back(temp_node);
            delete_eids.push_back(temp_eid);
        }
    }

    // Handle underflow
    for (unsigned i = 0; i < delete_oids.size(); i++)
    {
        int eid = findEntry(delete_nodes[i], delete_oids[i]);
        if (eid != -1)
        {
            deleteEntry(delete_nodes[i], eid);
        }
    }
}

// Delete data from graph
void GTI::deleteGraph(Objects *delete_data, std::vector<unsigned> &delete_oids)
{
    // Update entries_sec
    std::vector<GTI_Node *> nodes;
    nodes.push_back(root);
    unsigned size = nodes.size();
    for (unsigned i = 0; i < height - 1; i++)
    {
        for (unsigned j = 0; j < size; ++j)
        {
            if (i < height - 2) // Upper level
                for (unsigned k = 0; k < nodes[j]->entries.size(); k++)
                    nodes.push_back(nodes[j]->entries[k]->child);
            else // Second level
            {
                // Update entries of second level
                for (unsigned k = 0; k < nodes[j]->entries.size(); k++)
                {
                    unsigned oid = nodes[j]->entries[k]->oid;
                    entries_sec[map[oid]] = nodes[j]->entries[k];
                }
            }
        }
        nodes.erase(nodes.begin(), nodes.begin() + size);
        size = nodes.size();
    }

    // Delete in degree neighbors from graph
    unsigned delete_size = delete_oids.size();
    std::vector<unsigned> reinsert_gids;      // Ids of data needed to be reinserte
    std::vector<unsigned> reverse_cands_oids; // Possible reverse neighbor candidates
    unsigned reinsert_size = 0;
#pragma omp parallel for
    for (unsigned i = 0; i < delete_oids.size(); i++)
    {
        if (map[delete_oids[i]] == -1)
            continue;
        float radius = sqrt(index_hnsw->getRadius(map[delete_oids[i]])); // Get in degree radius
        std::vector<Neighbor> result;
        searchTreeRange(data->vecs[delete_oids[i]].data(), radius, result); // Range search to find possible reverse neighbors

        // Possible reverse neighbors = Range search result + Delete data
        std::vector<unsigned> reverse_cands_oids; // Possible reverse neighbor candidates
        for (unsigned j = 0; j < result.size(); j++)
            reverse_cands_oids.push_back(result[j].id);
        reverse_cands_oids.insert(reverse_cands_oids.end(), delete_oids.begin(), delete_oids.end());
        std::sort(reverse_cands_oids.begin(), reverse_cands_oids.end());
        reverse_cands_oids.erase(std::unique(reverse_cands_oids.begin(), reverse_cands_oids.end()), reverse_cands_oids.end());

        // Delete reverse neighbors
        std::vector<unsigned> local_reinsert_gids;
        for (unsigned j = 0; j < reverse_cands_oids.size(); j++)
        {
            if (map[reverse_cands_oids[j]] != -1 && entries_sec[map[reverse_cands_oids[j]]] != nullptr)
            {
                auto it = std::find(reinsert_gids.begin(), reinsert_gids.end(), map[reverse_cands_oids[j]]);
                if (it == reinsert_gids.end())
                {
// OpenMP critical section to avoid race condition on reinsert_gids
#pragma omp critical
                    {
                        index_hnsw->deleteNeighbor(map[reverse_cands_oids[j]], map[delete_oids[i]], local_reinsert_gids); // Delete reverse neighbors
                    }
                }
            }
        }

// OpenMP critical section to update reinsert_gids
#pragma omp critical
        {
            reinsert_gids.insert(reinsert_gids.end(), local_reinsert_gids.begin(), local_reinsert_gids.end());
        }

        // If nodes in graph have no neighbor at some level, delete them and add them into reinsert list
        unsigned local_reinsert_size = local_reinsert_gids.size();
#pragma omp critical
        {
            for (unsigned j = reinsert_size; j < reinsert_gids.size(); j++)
                if (entries_sec[reinsert_gids[j]] != nullptr)
                    delete_oids.push_back(entries_sec[reinsert_gids[j]]->oid);
            reinsert_size += local_reinsert_size;
        }
    }

    // Delete data
    for (unsigned i = 0; i < delete_size; i++)
    {
        if (map[delete_oids[i]] != -1)
        {
            index_hnsw->deleteData(map[delete_oids[i]]); // Delete data from graph
            map[delete_oids[i]] = -1;
        }
        std::vector<float>().swap(data->vecs[delete_oids[i]]); // Delete data from data list
    }

    index_hnsw->reinsertData(reinsert_gids); // Reinsert data into graph

    // Rebuild the graph model
    index_hnsw->UnloadModel();
    index_hnsw->buildFromDeletion();
}

// Delete entry
void GTI::deleteEntry(GTI_Node *node, unsigned eid)
{
    if (node == nullptr || eid < 0 || eid >= node->entries.size())
    {
        printf("Invalid node or eid in deleteEntry\n");
        return;
    }

    // Delete entry
    delete node->entries[eid];
    node->entries[eid] = nullptr;
    node->entries.erase(node->entries.begin() + eid);

    if (node->entries.size() == 0) // Current node is empty, delete the node and delete the entry upward
    {
        GTI_Node *parent_node = node->parent_node;
        int parent_eid = findParentEntry(parent_node, node);
        if (node->type == 1)
            entries_sec[map[(parent_node->entries[parent_eid]->oid)]] = nullptr;
        delete node;
        node = nullptr;
        deleteEntry(parent_node, parent_eid);
    }
    else if (node == root && node->entries.size() == 1) // Delete diffusion to root
    {
        root = node->entries[0]->child;
        root->parent_node = nullptr;
        height--;
        delete node->entries[0];
        node->entries[0] = nullptr;
        node->entries.erase(node->entries.begin());
        delete node;
        node = nullptr;
    }
}

// Find the leaf of the data
void GTI::findLeaf(float *query, GTI_Node *&node, unsigned &eid)
{
    Distance *distance = new Distance();
    std::queue<ND> cands; // Candidate set
    cands.push(ND(root, INF_DIS, INF_DIS));
    float r = 0;

    while (!cands.empty())
    {
        ND nd = cands.front();
        cands.pop();

        if (nd.node->type == 0) // Internal node
        {
            for (unsigned i = 0; i < nd.node->entries.size(); i++)
            {
                if (abs(nd.dis_p_q - nd.node->entries[i]->dis_p) <= r + nd.node->entries[i]->radius) // Parent pruning
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis_r = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    float dis_min = std::max(dis_r - nd.node->entries[i]->radius, float(0.0));
                    if (dis_min <= r) // Rounting object pruning
                    {
                        cands.push(ND(nd.node->entries[i]->child, dis_min, dis_r));
                    }
                }
            }
        }
        else // Leaf node
        {
            for (unsigned i = 0; i < nd.node->entries.size(); i++)
            {
                if (abs(nd.dis_p_q - nd.node->entries[i]->dis_p) <= r)
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    if (dis <= r)
                    {
                        bool is_same = true;
                        for (unsigned j = 0; j < data->dim; j++)
                        {
                            if (*(query + j) != data->vecs[oid][j])
                            {
                                is_same = false;
                                break;
                            }
                        }
                        if (is_same)
                        {
                            node = nd.node;
                            eid = i;
                        }
                    }
                }
            }
        }
    }

    delete distance;
    distance = NULL;
}

// kNN search for tree
void GTI::searchTreeKnn(float *query, unsigned k, std::priority_queue<Neighbor, std::vector<Neighbor>, std::less<Neighbor>> &res)
{
    std::priority_queue<ND, std::vector<ND>, std::greater<ND>> cands; // Candidate set; Ascending order
    Distance *distance = new Distance();

    // Initialization
    ND nd;
    nd.node = root;
    nd.dis = 0;
    cands.push(nd);
    for (unsigned i = 0; i < k; i++)
    {
        Neighbor nn;
        nn.dis = INF_DIS;
        res.push(nn);
    }

    // Search tree
    while (!cands.empty())
    {
        ND nd = cands.top();
        cands.pop();
        if (nd.dis > res.top().dis)
            break;

        for (unsigned i = 0; i < nd.node->entries.size(); i++)
        {
            bool parent_flag = true;
            if (nd.node != root)
            {
                if (abs(nd.dis_p_q - nd.node->entries[i]->dis_p) > res.top().dis + nd.node->entries[i]->radius) // Parent pruning
                    parent_flag = false;
            }
            if (parent_flag)
            {
                if (nd.node->type == 0) // Internal node
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis_r = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    float dis_min = std::max(dis_r - nd.node->entries[i]->radius, float(0.0));
                    if (dis_min <= res.top().dis) // Rounting object pruning
                    {
                        ND cand;
                        cand.node = nd.node->entries[i]->child;
                        cand.dis = dis_min;
                        cand.dis_p_q = dis_r;
                        cands.push(cand);
                        // float dis_max = dis_r + nd.node->entries[i]->radius;
                        // if (dis_max < res.top().dis) // Update top k results
                        // {
                        //     Neighbor nn;
                        //     nn.dis = dis_max;
                        //     res.push(nn);
                        //     if (res.size() > k)
                        //         res.pop();
                        // }
                    }
                }
                else // Leaf node
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    if (dis <= res.top().dis) // Update top k results
                    {
                        Neighbor nn;
                        nn.dis = dis;
                        nn.id = oid;
                        res.push(nn);
                        if (res.size() > k)
                            res.pop();
                    }
                }
            }
        }
    }

    delete distance;
    distance = NULL;
}

// Range search for tree
void GTI::searchTreeRange(float *query, float r, std::vector<Neighbor> &results)
{
    Distance *distance = new Distance();
    std::queue<ND> cands; // Candidate set
    cands.push(ND(root, INF_DIS, INF_DIS));

    while (!cands.empty())
    {
        ND nd = cands.front();
        cands.pop();

        if (nd.node->type == 0) // Internal node
        {
            for (unsigned i = 0; i < nd.node->entries.size(); i++)
            {
                if (abs(nd.dis_p_q - nd.node->entries[i]->dis_p) <= r + nd.node->entries[i]->radius) // Parent pruning
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis_r = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    float dis_min = std::max(dis_r - nd.node->entries[i]->radius, float(0.0));
                    if (dis_min <= r) // Rounting object pruning
                    {
                        cands.push(ND(nd.node->entries[i]->child, dis_min, dis_r));
                    }
                }
            }
        }
        else // Leaf node
        {
            for (unsigned i = 0; i < nd.node->entries.size(); i++)
            {
                if (abs(nd.dis_p_q - nd.node->entries[i]->dis_p) <= r)
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    if (dis <= r)
                        results.push_back(Neighbor(oid, dis, true));
                }
            }
        }
    }

    delete distance;
    distance = NULL;
}

// Search
void GTI::search(float *query, unsigned L, unsigned K, std::vector<Neighbor> &results)
{
    std::vector<std::pair<int, float>> results_hnsw; // Results of search HNSW

    std::vector<float> vec;
    vec.assign(query, query + data->dim);
    index_hnsw->SearchByVectorM(vec, L, 5 * L, results_hnsw, results, entries_sec, data->vecs); // Search
}

// Exact k-NN search
void GTI::searchExactKnn(float *query, unsigned L, unsigned K, std::vector<Neighbor> &results,
                         std::priority_queue<Neighbor, std::vector<Neighbor>, std::less<Neighbor>> &res)
{
    // Search graph to get initial results
    std::vector<std::pair<int, float>> results_hnsw; // Results of search HNSW
    // std::vector<Neighbor> results_graph;
    std::vector<float> vec;
    vec.assign(query, query + data->dim);
    index_hnsw->SearchByVectorM(vec, L, 5 * L, results_hnsw, results, entries_sec, data->vecs); // Search graph

    // Search tree using graph results to get final k-NNs
    for (unsigned i = 0; i < K; i++)
    {
        Neighbor nn;
        nn.dis = sqrt(results[i].dis);
        nn.id = results[i].id;
        res.push(nn);
    }
    searchTree(query, K, res);
    unsigned i = 0;
    while (!res.empty())
    {
        results[K - 1 - i] = res.top();
        res.pop();
        i++;
    }
}

// Search tree using graph results
void GTI::searchTree(float *query, unsigned k, std::priority_queue<Neighbor, std::vector<Neighbor>, std::less<Neighbor>> &res)
{
    std::priority_queue<ND, std::vector<ND>, std::greater<ND>> cands; // Candidate set; Ascending order
    Distance *distance = new Distance();

    // Initialization
    ND nd;
    nd.node = root;
    nd.dis = 0;
    cands.push(nd);
    // for (unsigned i = 0; i < k; i++)
    // {
    //     Neighbor nn;
    //     nn.dis = INF_DIS;
    //     res.push(nn);
    // }

    // Search tree
    while (!cands.empty())
    {
        ND nd = cands.top();
        cands.pop();
        if (nd.dis > res.top().dis)
            break;

        for (unsigned i = 0; i < nd.node->entries.size(); i++)
        {
            bool parent_flag = true;
            if (nd.node != root)
            {
                if (abs(nd.dis_p_q - nd.node->entries[i]->dis_p) > res.top().dis + nd.node->entries[i]->radius) // Parent pruning
                    parent_flag = false;
            }
            if (parent_flag)
            {
                if (nd.node->type == 0) // Internal node
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis_r = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    float dis_min = std::max(dis_r - nd.node->entries[i]->radius, float(0.0));
                    if (dis_min <= res.top().dis) // Rounting object pruning
                    {
                        ND cand;
                        cand.node = nd.node->entries[i]->child;
                        cand.dis = dis_min;
                        cand.dis_p_q = dis_r;
                        cands.push(cand);
                        // float dis_max = dis_r + nd.node->entries[i]->radius;
                        // if (dis_max < res.top().dis) // Update top k results
                        // {
                        //     Neighbor nn;
                        //     nn.dis = dis_max;
                        //     res.push(nn);
                        //     if (res.size() > k)
                        //         res.pop();
                        // }
                    }
                }
                else // Leaf node
                {
                    unsigned oid = nd.node->entries[i]->oid;
                    float dis = distance->getDisP(data->vecs[oid].data(), query, data->type, data->dim);
                    if (dis <= res.top().dis) // Update top k results
                    {
                        Neighbor nn;
                        nn.dis = dis;
                        nn.id = oid;
                        res.push(nn);
                        if (res.size() > k)
                            res.pop();
                    }
                }
            }
        }
    }

    delete distance;
    distance = NULL;
}

// Get the size of tree
void GTI::getTreeSize()
{
    std::vector<GTI_Node *> nodes;
    nodes.push_back(root);

    // Get the size of tree
    unsigned size = nodes.size();
    for (unsigned i = 0; i < height; i++)
    {
        for (unsigned j = 0; j < size; ++j)
        {
            for (unsigned k = 0; k < nodes[j]->entries.size(); k++)
            {
                tree_size += sizeof(unsigned) + 2 * sizeof(float) + sizeof(GTI_Node *);
                if (i < height - 1) // Upper level
                {
                    nodes.push_back(nodes[j]->entries[k]->child);
                }
            }
            // tree_size += sizeof(unsigned) + sizeof(GTI_Node *) + sizeof(GTI_Entry *) * nodes[j]->entries.size();
        }
        nodes.erase(nodes.begin(), nodes.begin() + size);
        size = nodes.size();
    }
}
