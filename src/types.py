# memory can be to/from/bi
TO_PROCESSOR = 1
FROM_PROCESSOR = 0
BIDIRECTIONAL = 2
def direction_string(direction):
    if direction == TO_PROCESSOR:
        return 'TO_PROCESSOR' 
    elif direction == FROM_PROCESSOR:
        return 'FROM_PROCESSOR'
    elif direction == BIDIRECTIONAL:
        return 'BIDIRECTIONAL'
    else:
        raise RuntimeError('Unknown direction')
def direction_from_string(dirstr):
    if dirstr == 'To Processor':
        return TO_PROCESSOR 
    elif dirstr == 'From Processor':
        return FROM_PROCESSOR
    elif dirstr == 'To/From Processor':
        return BIDIRECTIONAL
    else:
        raise RuntimeError('Unknown direction')

LISTDELIMIT = ','
PORTDELIMIT = ':'
