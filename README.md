## Make Handle (TopMod)

This is a Blender addon that ports the "Connect Faces" feature from [TopMod](http://people.tamu.edu/~ergun/research/topology/download.html), a research 3D modeling program. Given two faces and vertices adjacent to those faces, it will create a loopy segmented "handle" that connects the faces together, possibly with twists.

### Installation

Tested with Blender 3.3.

- Go to Edit -> Preferences.
- Click "Addons" on the left.
- Click "Install..." in the upper right.
- Select the file `make_handle.py`.
- Click "Install Add-on."
- Click the checkbox to the left of "Mesh: Make Handle."

### Usage

To make a handle:

- Select a mesh and enter edit mode.
- Enter face selection mode (near the upper left of the 3D view).
- Select two faces (use Shift-click to select multiple).
- Go to Edit -> Menu Search, or press F3. Search for "Select Face for Handle" and press Enter.
- Enter vertex selection mode.
- Select two vertices, one adjacent to each face, or select one vertex adjacent to both faces.
- Go to Edit -> Menu Search, search for "Make Handle," and press Enter.

This is pretty awkward. The workflow will be improved in the future.

### Limitations

The polygons must have the same number of sides.

No parameters yet.