"""Read the study settings and work out derived sizes."""
import yaml


def load_settings(path='study.yaml'):
    with open(path) as f: #reads the yaml and returns it as a dictionary
        return yaml.safe_load(f) #the safe way to read yaml


def channel_width(n_channels, plate):
    usable = plate['width'] - 2 * plate['edge_margin'] #the width left for channels and metal strips after removing the edge margin on both sides
    return (usable - (n_channels - 1) * plate['wall']) / n_channels


if __name__ == '__main__':
    settings = load_settings()
    plate = settings['plate']
    channel_length = plate['length'] - plate['inlet_header'] - plate['outlet_header']
    print(f'Channel length: {channel_length} mm')
    for n in range(settings['channels']['min'], settings['channels']['max'] + 1): #loops throgh every number of channels from the min to the max, .range does not include the last number in the rage so we do + 1
        print(f'{n:2d} channels: {channel_width(n, plate):5.1f} mm wide')