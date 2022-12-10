# Make Handle (Blender addon port of a TopMod feture)

This is a Blender addon that ports the "Connect Faces" feature from [TopMod](http://people.tamu.edu/~ergun/research/topology/download.html), a research 3D modeling program. Given two faces and vertices adjacent to those faces, it will create a loopy segmented "handle" that connects the faces together, possibly with twists.

## Installation

Tested with Blender 3.3.

- Go to Edit -> Preferences.
- Click "Addons" on the left.
- Click "Install..." in the upper right.
- Select the file `make_handle.py` and click "Install Add-on."
- Click the checkbox to the left of "Mesh: Make Handle."

## Usage

To make a handle:

- Select a mesh and enter edit mode.
- Enable face selection and vertex selection modes near the upper left of the 3D view. Use Shift+click to combine the modes.
- Make sure nothing is selected.
- Select two vertices. You may also select just one vertex if the faces share that vertex.
- Select two faces, one adjacent to each of those vertices. Make sure not to click on any vertices, or you'll have to start over. (It may look like Blender clobbers your vertex selection, but it actually does remember which vertices you selected originally.)
- Go to Edit -> Menu Search, search for "Make Handle," and press Enter.
- Open up the panel in the bottom left and adjust the following parameters to taste:
  - **Segments:** number of segments in the handle.
  - **Weight 1:** controls how much the handle sticks out for the first selected face.
  - **Symmetric Weights:** if checked, Weight 2 is overriden to be equal to Weight 1.
  - **Weight 2:** controls how much the handle sticks out for the second selected face.
  - **Twists:** number of additional 360-degree polygonal twists added. Negative values will twist in the opposite direction.
- Click away from the panel to confirm.

There is no requirement that the faces are identical, or even have the same number of sides. The two polygons are converted to polar coordinates in their respective planes, which are then linearly interpolated. If the faces have different vertex counts, the addon will treat the smaller polygon as having several coincident vertices bunched up.

If both vertices are adjacent to both faces, then the choice of which vertex corresponds to which face may be ambiguous. In such cases, the order of selection resolves the ambiguity, with the first selected face matching the first selected vertex.

## License

This addon is a port of a feature from TopMod, which is licensed under the GPL v2 or later.