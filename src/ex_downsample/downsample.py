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
    :param inputFile: ex file
    :return List of all values related to each node
    """
    node_index = 1
    allNodeData = []
    nodeValues = []
    copyValue = False

    for index, line in enumerate(open(inputFile)):
        node_pattern = "Node: %s" % node_index
        if re.match(node_pattern, line):
            allNodeData.append(nodeValues)
            nodeValues = []
            copyValue = True
            node_index += 1
            continue

        if copyValue == True:
            ln = line.split(' ')[2] if line.split(' ')[1] == '' else line.split(' ')[1]
            nodeValues.append(ln)

        if re.match('!#mesh mesh1d, dimension=1, nodeset=nodes', line):
            allNodeData.append(nodeValues)
            break

    return allNodeData


def getElementData(inputFile):
    """
    Extract nodes connectivity from ex file and store as list.
    :param inputFile: ex file
    :return List of node connectivity for each element
    :return element header copied from input file
    """
    elementList = []
    get_element_node = False
    copyLines = False
    elementHeader = []

    for index, line in enumerate(open(inputFile)):
        if get_element_node:
            node1 = int(float(line.split(' ')[1]))
            node2 = int(float(line.split(' ')[2]))
            elementList.append([node1, node2])
            get_element_node = False
        if re.match(" Nodes:", line):
            get_element_node = True
        if re.match('!#mesh mesh1d, dimension=1, nodeset=nodes', line):
            copyLines = True
        if re.match('Element: 1', line):
            copyLines = False
        if copyLines:
            elementHeader.append(line)

    return elementList, elementHeader


def getNewNodeNumber(oldNodeNumber, newNodeNumberList, newNodeCount):
    """
    Check newNodeNumberList for new node numbering. If already assigned,
    return the assigned node numbering, else assign new number.
    :param oldNodeNumber: original node numbering
    :param newNodeNumberList: List that stores new node numbering
    :param newNodeCount: Count track for new node index
    : return: new node number, updated node number list and
    updated new node count
    """

    if newNodeNumberList[oldNodeNumber] == 0:
        newNodeCount += 1
        newNodeNumberList[oldNodeNumber] = newNodeCount
        newNodeNumber = newNodeCount
    else:
        newNodeNumber = newNodeNumberList[oldNodeNumber]

    return newNodeNumber, newNodeNumberList, newNodeCount


def downsample_ex(inputFile, outputFile, targetLength = 10):

    # Extract nodes and elements from ex file
    nodeData = getNodeData(inputFile)
    elementList, elementHeader = getElementData(inputFile)
    totalNodes = len(nodeData)
    # totalElements = len(elementList)

    # Create parent-child list & child-parent list
    childList = [] # stores node numbering of children
    clearedChildList = [] # stores nodes that have been taken care of
    parentList = [] # stores node numbering of parents
    for i in range(1,totalNodes+2):
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
    junctionCheck = [0] * (totalNodes+2)
    startNodeCheck = [0] * (totalNodes+2)
    endNodeCheck = [0] * (totalNodes+2)

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
    newNodeNumberList = [0] * (totalNodes+2)
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
                nx.append([float(nodeData[parentNode][c]) for c in range(3)])
                nx.append([float(nodeData[childNode][c]) for c in range(3)])
                branchNodes.append(parentNode)
                branchNodes.append(childNode)
                count = 0
                while not childAtEndOfBranch:
                    count += 1
                    assert count < 10000, 'Trapped in while loop' 
                    childNode = childList[childNode][0]
                    childAtEndOfBranch = (junctionCheck[childNode] == 1 or endNodeCheck[childNode] == 1 or childNode == parentNode)
                    nx.append([float(nodeData[childNode][c]) for c in range(3)])
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

                reducedElementCount = int(cumulativeLength // targetLength)
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

    print('Reduced number of nodes from', totalNodes-1, 'to', newNodeCount)

    # Find old node numbering of retained nodes
    oldNumberOfReducedNodes = [0]*(newNodeCount+1)
    for i in range(len(newNodeNumberList)):
        if newNodeNumberList[i] > 0:
            oldNumberOfReducedNodes[newNodeNumberList[i]] = i

    # Write output file
    numberOfValues = len(nodeData[1])
    # Copy file header from input file to output file
    for index, line in enumerate(open(inputFile)):
        with open(outputFile, 'a') as output:
            if not re.match("Node: 1", line):
                output.writelines(line)
            else:
                break

    # Write nodes and values
    for i in range(1, len(oldNumberOfReducedNodes)):
        with open(outputFile, 'a') as output:
            output.writelines("Node: %s" % i + '\n')
            for j in range(numberOfValues):
                output.writelines(' ' + nodeData[oldNumberOfReducedNodes[i]][j])

    # Copy file element header from input file to output file
    copyLines = False
    for i in range(len(elementHeader)):
        with open(outputFile, 'a') as output:
            output.writelines(elementHeader[i])

    # Write elements to output file
    for i in range(len(reducedElementList)):
        with open(outputFile, 'a') as output:
            output.writelines("Element: %s" % (i+1) + '\n')
            output.writelines(" Nodes:" + '\n')
            output.writelines(" %s %s" % (reducedElementList[i][0], reducedElementList[i][1]) + '\n')


def main():
    args = parse_args()
    if os.path.exists(args.inputFile):

        if args.outputFile is None:
            fileName = args.inputFile.split('.')[0]
            outputFile = fileName + '_reducedTest.ex'
        else:
            outputFile = args.outputFile + '.ex'

        if os.path.exists(outputFile):
            os.remove(outputFile)

        if args.target_distance is None:
            target_distance = 10
        else:
            target_distance = int(args.target_distance)

        downsample_ex(args.inputFile, outputFile, target_distance)


def parse_args():
    parser = argparse.ArgumentParser(description="Downsampling of ex file.")
    parser.add_argument("inputFile", help="Location of the input file.")
    parser.add_argument("--outputFile", help="Location of the output downsampled file. "
                                                "[defaults to the location of the input file if not set.]")
    parser.add_argument("--target_distance", help="Target distance between downsampled points. "
                                                      "[default is 10.]")

    program_arguments = ProgramArguments()
    parser.parse_args(namespace=program_arguments)

    return program_arguments


if __name__ == '__main__':
    main()
