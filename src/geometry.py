"""Build the 2D cold plate geometry and mesh with gmsh, for any number of channels."""
import sys #to read the number of channels typed on the terminal
import gmsh #geometry and meshing library
from config import load_settings, channel_width

MM = 0.001  # OpenFOAM works in metres, so every length in mm is multiplied by this


def build_plate(n_channels, settings, out_file, show=False): #t takes the number of channels, the settings, the file name to save, and whether to open the gmsh viewer
    plate = settings['plate']
    L, W = plate['length'], plate['width']
    edge, wall = plate['edge_margin'], plate['wall']
    x0 = plate['inlet_header']
    x1 = L - plate['outlet_header']
    pw, pl = plate['port_width'], plate['port_length']
    w = channel_width(n_channels, plate)
    cell = settings['mesh']['cell_size'] * MM

    gmsh.initialize()
    gmsh.option.setNumber('General.Verbosity', 2) #sets how much gmsh prints. 2 means warnings and errors only
    gmsh.model.add(f'plate_{n_channels}') #creates a new, empty model, named after the number of channels
    occ = gmsh.model.occ #a short name for gmsh’s OpenCASCADE geometry tools, the CAD engine that can join and cut shapes, like Fusion’s combine tool

    cavity = occ.addRectangle(0, edge * MM, 0, L * MM, (W - 2 * edge) * MM)
    inlet = occ.addRectangle(-pl * MM, (W - pw) / 2 * MM, 0, pl * MM, pw * MM)
    outlet = occ.addRectangle(L * MM, (W - pw) / 2 * MM, 0, pl * MM, pw * MM)
    fluid, _ = occ.fuse([(2, cavity)], [(2, inlet), (2, outlet)]) #joins the cavity and both ports into one shape, 2 means surface. fuse returns two things, and _ is Python’s way of saying “I don’t need the second one"

    strips = [] #empty list for metal strips
    for i in range(1, n_channels): #1 strip between each pair of channels, so N − 1 strips (i = 1 to N − 1)
        y = edge + i * w + (i - 1) * wall #strip i starts across the plate: the edge margin, plus i channels, plus the i − 1 strips before it
        strips.append((2, occ.addRectangle(x0 * MM, y * MM, 0, (x1 - x0) * MM, wall * MM))) ##draws that strip, from x0 to x1 along the plate, and wall (5 mm) wide, and adds it to the list
    fluid, _ = occ.cut(fluid, strips) #cuts all the strips out of the coolant reigon

    occ.extrude(fluid, 0, 0, cell, numElements=[1], recombine=True) #pulls the flat shape up in z by one cell size, with exactly 1 cell through the thickness (numElements=[1]). recombine=True makes the cells blocks (hexahedra) rather than wedges. Just like the cavity tutorial: a 2D case in OpenFOAM is a 3D mesh one cell thick
    occ.synchronize() #copies everything from the CAD engine into gmsh’s model, so the next steps can see it

    volume = gmsh.model.getEntities(3)[0][1] #finds the 3D coolant region. getEntities(3) lists all 3D shapes, [0] takes the first (the only one), and [1] takes its tag
    groups = {'inlet': [], 'outlet': [], 'heated_walls': [], 'walls': [], 'frontAndBack': []} #an empty list of each boundary name
    tol = 1e-5 #a tiny tolerance for comparing positions, because computers store decimals with tiny rounding errors
    for dim, tag in gmsh.model.getBoundary([(3, volume)], oriented=False): #goes through every face around the coolant reigon
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(dim, tag) #the smallest box that fits around that face, its minimum and maximum x, y and z. We use it to work out where each face is
        if abs(zmax - zmin) < tol: #the face is flat in z so it is the front or back face
            groups['frontAndBack'].append(tag)
        elif abs(xmax + pl * MM) < tol: #the face sits at x = −30 mm, the far end of the inlet port → inlet
            groups['inlet'].append(tag)
        elif abs(xmin - (L + pl) * MM) < tol: #the face sits at x = 430 mm, the far end of the outlet port → outlet
            groups['outlet'].append(tag)
        elif xmin > x0 * MM - tol and xmax < x1 * MM + tol:
            groups['heated_walls'].append(tag) #the face lies entirely within the channel section (x from 30 to 370): the sides of the metal strips → heated_walls, where the batteries’ heat goes in
        else:
            groups['walls'].append(tag)

    for name, tags in groups.items(): #goes through each group
        gmsh.model.addPhysicalGroup(2, tags, name=name) #and names those faces in gmsh. These become the patch names in OpenFOAM
    gmsh.model.addPhysicalGroup(3, [volume], name='fluid') #names the 3D reigon itself

    gmsh.option.setNumber('Mesh.CharacteristicLengthMax', cell) #no cell bigger than cell (2mm)
    gmsh.option.setNumber('Mesh.Algorithm', 8) #a meshing method that is good at making 4-sided cells
    gmsh.option.setNumber('Mesh.RecombineAll', 1) #turn triangles into quadrilaterals wherever possible. OpenFOAM prefers them
    gmsh.option.setNumber('Mesh.MshFileVersion', 2.2) #save in the older file format, the one OpenFOAM’s gmshToFoam reads
    gmsh.model.mesh.generate(3) #makes the mesh
    gmsh.write(out_file) #saves it to a file

    print(f'{n_channels} channels, {w:.1f} mm wide')
    for name, tags in groups.items(): #prints how many faces ended up in each boundary group, a quick check that the naming worked
        print(f'  {name}: {len(tags)} faces')
    if show:
        gmsh.fltk.run() #if you asked for it, opens gmsh’s own viewer window so you can see the mesh
    gmsh.finalize() #closes gmsh properly


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6 #the number of channels you type after the script name, or 6 if you don’t type one. int turns the text “8” into the number 8
    show = '--show' in sys.argv #True if --show is typed anywhere in the command
    build_plate(n, load_settings(), f'plate_N{n}.msh', show) #builds and saves the plate