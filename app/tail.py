# tail of text file
# https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-similar-to-tail
# I've chosen one of the simpler implmentations, good enough if you only need to go back 1K bytes or so
# File must be read a binary in case it is Unicode.
def tail(f, lines=20):
    '''
    :param f: file opened with 'rb' mode
    :param lines: number of lines you want to return
    :return: string of all the lines with '\n' separator
    '''
    total_lines_wanted = lines

    BLOCK_SIZE = 1024
    f.seek(0, 2)
    block_end_byte = f.tell()
    file_end_byte = block_end_byte
    lines_to_go = total_lines_wanted
    block_number = 1
    blocks = []
    while lines_to_go > 0 and block_end_byte > 0:
        if (block_end_byte - BLOCK_SIZE > 0):
            # backup by block_number, but negative seek relative to EOF is not allowd for text files!
            f.seek(file_end_byte - block_number*BLOCK_SIZE, 0)
            blocks.append(f.read(BLOCK_SIZE))
        else:
            f.seek(0,0)
            blocks.append(f.read(block_end_byte))
        lines_found = blocks[-1].count('\n')
        lines_to_go -= lines_found
        block_end_byte -= BLOCK_SIZE
        block_number += 1
    all_read_text = ''.join(reversed(blocks))
    return '\n'.join(all_read_text.splitlines()[-total_lines_wanted:])
