# Open a file with access mode 'a'
file_object = open('sample.txt', 'a')
# Append 'hello' at the end of file
file_object.write('{0}:{1}:{2}\n'.format('ss','ss','ss'))
# Close the file
file_object.close()