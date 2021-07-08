"""
A simple function to reduce ex node points by sampling
arclength between junctions into target distance.
"""

import os
import argparse
import re
import math


class ProgramArguments(object):
    pass


def getNodeData(inputFile):
    """
    Extract values of nodes from ex file and store as list.
    :param inputFile: exnode file
    :return List of all values related to each node
    """
    node_index = 1
    allNodeData = []
    originalNodeNumber = [0]
    nodeValues = []
    copyValue = False

    for index, line in enumerate(open(inputFile)):
        nodeLine = (line.split(' ')[0] == 'Node:')
        if nodeLine:
            node_index = line.split(' ')[1]
            nodeValues = []
            copyValue = True
            allNodeData.append(nodeValues)
            originalNodeNumber.append(int(node_index))
            continue

        if copyValue == True:
            ln = line.split(' ')[2] if line.split(' ')[1] == '' else line.split(' ')[1]
            nodeValues.append(ln)

    allNodeData.append(nodeValues)

    return allNodeData, originalNodeNumber


def getElementData(inputFile):
    """
    Extract nodes connectivity from ex file and store as list.
    :param inputFile: exelem file
    :return List of node connectivity for each element
    """
    elementList = []
    get_element_node = False
    copyLines = True
    elementHeader = []

    for index, line in enumerate(open(inputFile)):
        elementLine = (line.split(' ')[1] == 'Element:')
        if elementLine:
            element_index = line.split(' ')[2]
        if get_element_node:
            node1 = int(float(line.split(' ')[1]))
            node2 = int(float(line.split(' ')[2]))
            elementList.append([node1, node2])
            get_element_node = False
        if re.match(" Nodes:", line):
            get_element_node = True

    return elementList


def getNewNodeNumber(oldNodeNumber, newNodeNumberList, newNodeCount):
    """
    Check newNodeNumberList for new node numbering. If already assigned,
    return the assigned node numbering, else assign new number.
    :param oldNodeNumber: original node numbering
    :param newNodeNumberList: List that stores new node numbering
    :param newNodeCount: Count track for new node index
    :return new node number, updated node number list and
    updated new node count
    """

    if newNodeNumberList[oldNodeNumber] == 0:
        newNodeCount += 1
        newNodeNumberList[oldNodeNumber] = newNodeCount
        newNodeNumber = newNodeCount
    else:
        newNodeNumber = newNodeNumberList[oldNodeNumber]

    return newNodeNumber, newNodeNumberList, newNodeCount

def writeNodesToFile(inputNodeFile, outputNodeFile, compressedNodeNumberList, oldNumberOfReducedNodes, nodeData, numberOfValues):
    """
    Copy file header from input file to output file. Write nodes
    and values to output file.
    :param inputNodeFile: Input exnode file
    :param outputNodeFile: New exnode file with reduced nodes
    :param compressedNodeNumberList: In stomach files, there are gaps
    between node numberings. This list records the new node numbering
    after removing the gaps
    :param oldNumberOfReducedNodes: List of old node numbering for
    retained nodes
    :param nodeData: Node coordinates and values
    :numberOfValues: Number of values for each node
    """

    # Copy file header from input file to output file
    for index, line in enumerate(open(inputNodeFile)):
        with open(outputNodeFile, 'a') as output:
            if not re.match("Node: 1", line):
                output.writelines(line)
            else:
                break

    # Write nodes and values
    for i in range(1, len(oldNumberOfReducedNodes)):
        with open(outputNodeFile, 'a') as output:
            output.writelines("Node: %s" % i + '\n')
            for j in range(numberOfValues):
                output.writelines(' ' + nodeData[compressedNodeNumberList[oldNumberOfReducedNodes[i]]-1][j])

    return

def downsample_ex(inputNode0File, inputNode1File, inputNode2File, inputElemFile, outputNode0File, outputNode1File, outputNode2File, outputElemFile, targetLength = 10):

    # Extract nodes and elements from ex file
    node0Data, originalNodeNumberList = getNodeData(inputNode0File)
    node1Data, _ = getNodeData(inputNode1File)
    node2Data, _ = getNodeData(inputNode2File)
    elementList = getElementData(inputElemFile)
    totalNodes = len(node0Data)
    totalOriginalNodes = max(originalNodeNumberList)

    # Create compressedNodeNumber list
    lastOriginalNode = max(originalNodeNumberList)
    compressedNodeNumberList = [0] * (lastOriginalNode + 2)
    for i in range(len(originalNodeNumberList)):
        compressedNumber = i
        originalNodeNumber = originalNodeNumberList[i]
        compressedNodeNumberList[originalNodeNumber] = compressedNumber

    # Create parent-child list & child-parent list
    childList = [] # stores node numbering of children
    clearedChildList = [] # stores nodes that have been taken care of
    parentList = [] # stores node numbering of parents
    for i in range(1,totalOriginalNodes+2):
        childList.append([0, 0, 0, 0]) # expecting 4 children and parents but might expand later
        parentList.append([0, 0, 0, 0])
        clearedChildList.append([0, 0, 0, 0])

    for element in range(len(elementList)):
        parentNode = elementList[element][0]
        childNode = elementList[element][1]
        i = 0
        while childList[parentNode][i] != 0:
            i += 1
            assert i < 4, 'More than 4 children detected'
        childList[parentNode][i] = childNode
        clearedChildList[parentNode][i] = childNode
        i = 0
        while parentList[childNode][i] != 0:
            i += 1
            assert i < 4, 'More than 4 parents detected'
        parentList[childNode][i] = parentNode

    #Identify start nodes, end nodes and junctions
    junctionCheck = [0] * (totalOriginalNodes+2)
    startNodeCheck = [0] * (totalOriginalNodes+2)
    endNodeCheck = [0] * (totalOriginalNodes+2)

    for i in range(len(childList)):
        if childList[i][0] == 0:
            endNodeCheck[i] = 1
        if childList[i][1] > 0:
            junctionCheck[i] = 1
        if parentList[i][0] == 0:
            startNodeCheck[i] = 1
        if parentList[i][1] > 0:
            junctionCheck[i] = 1

    # Find points in a branch
    newNodeNumberList = [0] * (totalOriginalNodes+2)
    reducedElementList = []
    newNodeCount = 0

    for element in range(len(elementList)):
        parentNode = elementList[element][0]
        if clearedChildList[parentNode][0] == 0: # No child / child already removed
            continue
        else:
            childNode = elementList[element][1]
            childAtEndOfBranch = (junctionCheck[childNode] == 1 or endNodeCheck[childNode] == 1)
            if childAtEndOfBranch:
                # Store parent and child node and connectivity
                # Check for new numbering for nodes
                parentNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(parentNode, newNodeNumberList, newNodeCount)
                childNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(childNode, newNodeNumberList, newNodeCount)
                reducedElementList.append([parentNewNodeNumber, childNewNodeNumber])
            else: # child is not the end of branch
                nx = []
                branchNodes = []
                nx.append([float(node0Data[compressedNodeNumberList[parentNode]-1][c]) for c in range(3)])
                nx.append([float(node0Data[compressedNodeNumberList[childNode]-1][c]) for c in range(3)])
                branchNodes.append(parentNode)
                branchNodes.append(childNode)
                count = 0
                while not childAtEndOfBranch:
                    count += 1
                    assert count < 10000, 'Trapped in while loop' 
                    childNode = childList[childNode][0]
                    childAtEndOfBranch = (junctionCheck[childNode] == 1 or endNodeCheck[childNode] == 1 or childNode == parentNode)
                    nx.append([float(node0Data[compressedNodeNumberList[childNode]-1][c]) for c in range(3)])
                    branchNodes.append(childNode)

                # Null nodes inside a branch
                for i in range(1, len(branchNodes)-1):
                    nodeInsideBranch = branchNodes[i]
                    clearedChildList[nodeInsideBranch][0] = 0

                # Down sample to target length between points within branch
                cumulativeLength = 0
                cumulativeLengthList = [0]
                for i in range(len(nx)-1):
                    cumulativeLength += math.sqrt((nx[i][0]-nx[i+1][0])*(nx[i][0]-nx[i+1][0]) +
                                                  (nx[i][1]-nx[i+1][1])*(nx[i][1]-nx[i+1][1]) +
                                                  (nx[i][2]-nx[i+1][2])*(nx[i][2]-nx[i+1][2]))
                    cumulativeLengthList.append(cumulativeLength)

                reducedElementCount = math.ceil(cumulativeLength / targetLength)
                if reducedElementCount > 0:
                    parentNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(parentNode, newNodeNumberList, newNodeCount)
                    for n in range(reducedElementCount):
                        distance = cumulativeLength/reducedElementCount * n
                        diff = [abs(cumulativeLengthList[c] - distance) for c in range(len(cumulativeLengthList))]
                        localNodeToRetain = diff.index(min(diff))
                        GlobalNodeToRetain = branchNodes[localNodeToRetain]
                        childNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(GlobalNodeToRetain, newNodeNumberList, newNodeCount)
                        reducedElementList.append([parentNewNodeNumber, childNewNodeNumber])
                        parentNode = GlobalNodeToRetain
                        parentNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(parentNode, newNodeNumberList, newNodeCount)
                    childNode = branchNodes[-1]
                    childNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(childNode, newNodeNumberList, newNodeCount)
                    reducedElementList.append([parentNewNodeNumber, childNewNodeNumber])
                else: # branch length is shorter than targetLength - keep parent and junction/end
                    parentNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(parentNode, newNodeNumberList, newNodeCount)
                    childNode = branchNodes[-1]
                    childNewNodeNumber, newNodeNumberList, newNodeCount = getNewNodeNumber(childNode, newNodeNumberList, newNodeCount)
                    reducedElementList.append([parentNewNodeNumber, childNewNodeNumber])

    print('Reduced number of nodes from', totalOriginalNodes-1, 'to', newNodeCount)

    # Find old node numbering of retained nodes
    oldNumberOfReducedNodes = [0]*(newNodeCount+1)
    for i in range(len(newNodeNumberList)):
        if newNodeNumberList[i] > 0:
            oldNumberOfReducedNodes[newNodeNumberList[i]] = i
    numberOfValues = len(node0Data[1])

    # Write output exnode files
    writeNodesToFile(inputNode0File, outputNode0File, compressedNodeNumberList, oldNumberOfReducedNodes, node0Data, numberOfValues)
    writeNodesToFile(inputNode1File, outputNode1File, compressedNodeNumberList, oldNumberOfReducedNodes, node1Data, numberOfValues)
    writeNodesToFile(inputNode2File, outputNode2File, compressedNodeNumberList, oldNumberOfReducedNodes, node2Data, numberOfValues)

    ## Write elements to output exelem file
    for index, line in enumerate(open(inputElemFile)):
        with open(outputElemFile, 'a') as output:
            if not re.match(" Element: 1 0 0", line):
                output.writelines(line)
            else:
                break

    for i in range(len(reducedElementList)):
        with open(outputElemFile, 'a') as output:
            output.writelines(" Element: %s 0 0" % (i+1) + '\n')
            output.writelines(" Nodes:" + '\n')
            output.writelines(" %s %s" % (reducedElementList[i][0], reducedElementList[i][1]) + '\n')
            output.writelines(" Scale factors:" + '\n')
            output.writelines("  1.000000000000000e+00  1.000000000000000e+00" + '\n')

def main():
    args = parse_args()
    if os.path.exists(args.inputNode0File):

        nodeFileName = args.inputNode0File.split('.')[0]
        outputNode0File = nodeFileName + 'reduced_0.exnode'
        outputNode1File = nodeFileName + 'reduced_1.exnode'
        outputNode2File = nodeFileName + 'reduced_2.exnode'

        elemFileName = args.inputElemFile.split('.')[0]
        outputElemFile = elemFileName + '_reduced.exelem'

        if args.target_distance is None:
            target_distance = 10
        else:
            target_distance = float(args.target_distance)

        downsample_ex(args.inputNode0File, args.inputNode1File, args.inputNode2File, args.inputElemFile, outputNode0File, outputNode1File, outputNode2File, outputElemFile, target_distance)

    return

def parse_args():
    parser = argparse.ArgumentParser(description="Downsampling of exnode and exelem files.")
    parser.add_argument("inputNode0File", help="Location of the input 0 exnode file.")
    parser.add_argument("--inputNode1File", help="Location of the input 1 exnode file.")
    parser.add_argument("--inputNode2File", help="Location of the input 2 exnode file.")
    parser.add_argument("--inputElemFile", help="Location of the input exelem file.")
    parser.add_argument("--target_distance", help="Target distance between downsampled points. "
                                                      "[default is 10.]")

    program_arguments = ProgramArguments()
    parser.parse_args(namespace=program_arguments)

    return program_arguments


if __name__ == '__main__':
    main()
