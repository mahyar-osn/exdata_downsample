"""
A simple function to reduce exdata node points. This version only works for exdata with
up to three explicit fields i.e. rectangular Cartesian coordinates, rgb, and radius. In future, a more general
framework will be implemented to handle different number and type of fields as well as different file formats
e.g. exf/ex2 formats to handle nodal derivatives and element interpolation.
"""

import os
import argparse
import re


class ProgramArguments(object):
    pass


def downsample(input_ex, output_ex, group_name, num_fields, factor=2):
    with open(output_ex, 'w') as exdata:
        if num_fields == 1:
            exdata.writelines(' Group name: %sByFactor%s\n' % (group_name, factor))
            exdata.writelines(' #Fields= 3\n')
            exdata.writelines(' 1) data_coordinates, coordinate, rectangular cartesian, #Components=3\n')
            exdata.writelines('   x.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   y.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   z.  Value index= 1, #Derivatives=0\n')
        elif num_fields == 2:
            exdata.writelines(' Group name: %sByFactor%s\n' % (group_name, factor))
            exdata.writelines(' #Fields= 3\n')
            exdata.writelines(' 1) data_coordinates, coordinate, rectangular cartesian, #Components=3\n')
            exdata.writelines('   x.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   y.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   z.  Value index= 1, #Derivatives=0\n')
            exdata.writelines(' 2) rgb, field, rectangular cartesian, real, #Components=3\n')
            exdata.writelines('   1.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   2.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   3.  Value index= 1, #Derivatives=0\n')
        elif num_fields == 3:
            exdata.writelines(' Group name: %sByFactor%s\n' % (group_name, factor))
            exdata.writelines(' #Fields= 3\n')
            exdata.writelines(' 1) data_coordinates, coordinate, rectangular cartesian, #Components=3\n')
            exdata.writelines('   x.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   y.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   z.  Value index= 1, #Derivatives=0\n')
            exdata.writelines(' 2) rgb, field, rectangular cartesian, real, #Components=3\n')
            exdata.writelines('   1.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   2.  Value index= 1, #Derivatives=0\n')
            exdata.writelines('   3.  Value index= 1, #Derivatives=0\n')
            exdata.writelines(' 3) radius, field, rectangular cartesian, real, #Components=1\n')
            exdata.writelines('   1.  Value index= 1, #Derivatives=0\n')
        else:
            ValueError('Invalid number of fields.')
            ValueError('Invalid number of fields.')

    node_index = 1
    new_node_index = 1
    count = 1
    field_count = 1
    coordinate_count = 1
    node_skip = False
    success = False
    for index, line in enumerate(open(input_ex)):
        with open(output_ex, 'a') as exdata:

            if new_node_index == 1 or count == factor:
                node_skip = False
                node_pattern = "Node: %s" % node_index
                node_match = re.match(node_pattern, line)

                if node_match:
                    success = True
                    exdata.writelines("Node: %s" % new_node_index + '\n')
                    count = 1
                    continue

            elif node_skip:
                node_index += 1
                count += 1
                node_skip = False
                continue

            elif not success:
                coordinate_count += 1
                if coordinate_count == 4:
                    coordinate_count = 1
                    node_skip = True
                continue

            if success:
                if line.split(' ')[1] == '':
                    ln = line.split(' ')[2]
                else:
                    ln = line.split(' ')[1]
                exdata.writelines(' ' + ln)

                field_count += 1
                if field_count == 8:
                    success = False
                    node_skip = True
                    node_index += 1
                    field_count = 1
                    new_node_index += 1


def main():
    args = parse_args()
    if os.path.exists(args.input_exdata):
        if args.output_exdata is None:
            output_ex = args.input_exdata + '_reduced.exdata'
        else:
            output_ex = args.output_exdata + '.exdata'

        if os.path.exists(output_ex):
            os.remove(output_ex)

        if args.group_name is None:
            group_name = 'ResampledExdata'
        else:
            group_name = args.group_name

        if args.number_of_fields is None:
            num_fields = 1
        else:
            num_fields = args.number_of_fields

        if args.downsampling_factor is None:
            downsample_factor = 2
        else:
            downsample_factor = int(args.downsampling_factor)

        downsample(args.input_exdata, output_ex, group_name, num_fields, factor=downsample_factor)


def parse_args():
    parser = argparse.ArgumentParser(description="Downsampling of exdata file.")
    parser.add_argument("input_exdata", help="Location of the input exdata file.")
    parser.add_argument("--output_exdata", help="Location of the output downsampled exdata file. "
                                                "[defaults to the location of the input file if not set.]")
    parser.add_argument("--group_name", help="Exdata group name. "
                                             "[default is 'ResampledExdata'.]")
    parser.add_argument("--number_of_fields", help="Number of fields in the data. "
                                                   "[default is 1.]")
    parser.add_argument("--downsampling_factor", help="A downsample factor to reduce the data file. "
                                                      "[default is 2.]")

    program_arguments = ProgramArguments()
    parser.parse_args(namespace=program_arguments)

    return program_arguments


if __name__ == '__main__':
    main()
