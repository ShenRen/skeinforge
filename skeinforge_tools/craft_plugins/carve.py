"""
Carve shape is a script to carve a list of slice layers.

Carve carves a list of slices into svg slice layers.  The 'Layer Thickness' is the thickness the extrusion layer at default extruder speed,
this is the most important carve preference.  The 'Perimeter Width over Thickness' is the ratio of the extrusion perimeter width to the
layer thickness.  The higher the value the more the perimeter will be inset, the default is 1.8.  A ratio of one means the extrusion is a
circle, a typical ratio of 1.8 means the extrusion is a wide oval.  These values should be measured from a test extrusion line.

Rarely changed preferences are 'Import Coarseness', 'Mesh Type', 'Infill in Direction of Bridges' & 'Layer Thickness over Precision'.
When a triangle mesh has holes in it, the triangle mesh slicer switches over to a slow algorithm that spans gaps in the mesh.  The
higher the import coarseness, the wider the gaps in the mesh it will span.  An import coarseness of one means it will span gaps the
of the perimeter width.  When the Mesh Type preference is Correct Mesh, the mesh will be accurately carved, and if a hole is found,
carve will switch over to the algorithm that spans gaps.  If the Mesh Type preference is Unproven Mesh, carve will use the gap
spanning algorithm from the start.  The problem with the gap spanning algothm is that it will span gaps, even if there is not actually a
gap in the model.  If the infill in direction of bridges preference is chosen, the infill will be in the direction of bridges across gaps, so
that the fill will be able to span a bridge easier.

The 'Layer Thickness over Precision' is the ratio of the layer thickness over the smallest change in value.  The higher the layer
thickness over precision, the more significant figures the output numbers will have, the default is ten.

The output will go from the "Layers From" index to the "Layers To" index.  The default for the "Layers From" index is zero and the
default for the "Layers To" is a really big number.  To get a single layer, set the "Layers From" to zero and the "Layers To" to one.

To run carve, in a shell type:
> python carve.py

The following examples carve the GNU Triangulated Surface file Screw Holder Bottom.stl.  The examples are run in a terminal in the
folder which contains Screw Holder Bottom.stl and carve.py.  The preferences can be set in the dialog or by changing the preferences file
'carve.csv' with a text editor or a spreadsheet program set to separate tabs.


> python carve.py
This brings up the dialog, after clicking 'Carve', the following is printed:
File Screw Holder Bottom.stl is being carved.
The carved file is saved as Screw Holder Bottom_carve.svg


>python
Python 2.5.1 (r251:54863, Sep 22 2007, 01:43:31)
[GCC 4.2.1 (SUSE Linux)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import carve
>>> carve.main()
File Screw Holder Bottom.stl is being carved.
The carved file is saved as Screw Holder Bottom_carve.svg
It took 3 seconds to carve the file.


>>> carve.writeOutput()
File Screw Holder Bottom.gcode is being carved.
The carved file is saved as Screw Holder Bottom_carve.svg
It took 3 seconds to carve the file.

"""

from __future__ import absolute_import
try:
	import psyco
	psyco.full()
except:
	pass
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from skeinforge_tools.skeinforge_utilities import euclidean
from skeinforge_tools.skeinforge_utilities import gcodec
from skeinforge_tools.skeinforge_utilities import preferences
from skeinforge_tools.skeinforge_utilities import triangle_mesh
from skeinforge_tools.skeinforge_utilities import interpret
from skeinforge_tools import polyfile
import cStringIO
import math
import os
import sys
import time
import webbrowser


__author__ = "Enrique Perez (perez_enrique@yahoo.com)"
__date__ = "$Date: 2008/02/05 $"
__license__ = "GPL 3.0"


def getCarving( fileName ):
	"Get a carving for the file using an import plugin."
	importPluginFilenames = interpret.getImportPluginFilenames()
	for importPluginFilename in importPluginFilenames:
		fileTypeDot = '.' + importPluginFilename
		if fileName[ - len( fileTypeDot ) : ].lower() == fileTypeDot:
			pluginModule = gcodec.getModule( importPluginFilename, 'import_plugins', os.path.dirname( __file__ ) )
			if pluginModule != None:
				return pluginModule.getCarving( fileName )
	print( 'Could not find plugin to handle ' + fileName )
	return None

def getCraftedText( fileName, text = '', carvePreferences = None ):
	"Get carved text."
	if gcodec.getHasSuffix( fileName, '.svg' ):
		if text == '':
			text = gcodec.getFileText( fileName )
		return text
	return getCraftedTextFromFileName( fileName, carvePreferences = None )

def getCraftedTextFromFileName( fileName, carvePreferences = None ):
	"Carve a shape file."
	carving = getCarving( fileName )
	if carving == None:
		return ''
	if carvePreferences == None:
		carvePreferences = CarvePreferences()
		preferences.getReadPreferences( carvePreferences )
	skein = CarveSkein()
	skein.parseCarving( carvePreferences, carving, fileName )
	return skein.output.getvalue()

def getDisplayedPreferences():
	"Get the displayed preferences."
	return preferences.getDisplayedDialogFromConstructor( CarvePreferences() )

def getParameterFromJavascript( lines, parameterName, parameterValue ):
	"Get a paramater from lines of javascript."
	for line in lines:
		strippedLine = line.replace( ';', ' ' ).lstrip()
		splitLine = strippedLine.split()
		firstWord = gcodec.getFirstWord( splitLine )
		if firstWord == parameterName:
			return float( splitLine[ 2 ] )
	return parameterValue

def getReplacedInQuotes( original, replacement, text ):
	"Replace what follows in quotes after the word."
	wordAndQuote = original + '="'
	originalIndexStart = text.find( wordAndQuote )
	if originalIndexStart == - 1:
		return text
	originalIndexEnd = text.find( '"', originalIndexStart + len( wordAndQuote ) )
	if originalIndexEnd == - 1:
		return text
	wordAndBothQuotes = text[ originalIndexStart : originalIndexEnd + 1 ]
	return text.replace( wordAndBothQuotes, wordAndQuote + replacement + '"' )

def getReplacedTagString( replacementTagString, tagID, text ):
	"Get text with the tag string replaced."
	idString = 'id="' + tagID + '"'
	idStringIndexStart = text.find( idString )
	if idStringIndexStart == - 1:
		return text
	tagBeginIndex = text.rfind( '<', 0, idStringIndexStart )
	tagEndIndex = text.find( '>', idStringIndexStart )
	if tagBeginIndex == - 1 or tagEndIndex == - 1:
		return text
	originalTagString = text[ tagBeginIndex : tagEndIndex + 1 ]
	return text.replace( originalTagString, replacementTagString )

def getReplacedWordAndInQuotes( original, replacement, text ):
	"Replace the word in the text and replace what follows in quotes after the word."
	text = text.replace( 'replaceWith' + original, replacement )
	return getReplacedInQuotes( original, replacement, text )

def writeOutput( fileName = '' ):
	"Carve a GNU Triangulated Surface file.  If no fileName is specified, carve the first GNU Triangulated Surface file in this folder."
	if fileName == '':
		unmodified = gcodec.getFilesWithFileTypesWithoutWords( interpret.getImportPluginFilenames() )
		if len( unmodified ) == 0:
			print( "There are no carvable files in this folder." )
			return
		fileName = unmodified[ 0 ]
	startTime = time.time()
	print( 'File ' + gcodec.getSummarizedFilename( fileName ) + ' is being carved.' )
	carveGcode = getCraftedText( fileName )
	if carveGcode == '':
		return
	suffixFilename = fileName[ : fileName.rfind( '.' ) ] + '_carve.svg'
	suffixDirectoryName = os.path.dirname( suffixFilename )
	suffixReplacedBaseName = os.path.basename( suffixFilename ).replace( ' ', '_' )
	suffixFilename = os.path.join( suffixDirectoryName, suffixReplacedBaseName )
	gcodec.writeFileText( suffixFilename, carveGcode )
	print( 'The carved file is saved as ' + gcodec.getSummarizedFilename( suffixFilename ) )
	print( 'It took ' + str( int( round( time.time() - startTime ) ) ) + ' seconds to carve the file.' )
	preferences.openWebPage( suffixFilename )


class CarvePreferences:
	"A class to handle the carve preferences."
	def __init__( self ):
		"Set the default preferences, execute title & preferences fileName."
		#Set the default preferences.
		self.archive = []
		self.fileNameInput = preferences.Filename().getFromFilename( interpret.getTranslatorFileTypeTuples(), 'Open File to be Carved', '' )
		self.archive.append( self.fileNameInput )
		self.importCoarseness = preferences.FloatPreference().getFromValue( 'Import Coarseness (ratio):', 1.0 )
		self.archive.append( self.importCoarseness )
		self.meshTypeLabel = preferences.LabelDisplay().getFromName( 'Mesh Type: ' )
		self.archive.append( self.meshTypeLabel )
		importRadio = []
		self.correctMesh = preferences.Radio().getFromRadio( 'Correct Mesh', importRadio, True )
		self.archive.append( self.correctMesh )
		self.unprovenMesh = preferences.Radio().getFromRadio( 'Unproven Mesh', importRadio, False )
		self.archive.append( self.unprovenMesh )
		self.infillBridgeThicknessOverLayerThickness = preferences.FloatPreference().getFromValue( 'Infill Bridge Thickness over Layer Thickness (ratio):', 1.0 )
		self.archive.append( self.infillBridgeThicknessOverLayerThickness )
		self.infillDirectionBridge = preferences.BooleanPreference().getFromValue( 'Infill in Direction of Bridges', True )
		self.archive.append( self.infillDirectionBridge )
		self.layerThickness = preferences.FloatPreference().getFromValue( 'Layer Thickness (mm):', 0.4 )
		self.archive.append( self.layerThickness )
		self.layerThicknessOverPrecision = preferences.FloatPreference().getFromValue( 'Layer Thickness over Precision (ratio):', 10.0 )
		self.archive.append( self.layerThicknessOverPrecision )
		self.layersFrom = preferences.IntPreference().getFromValue( 'Layers From (index):', 0 )
		self.archive.append( self.layersFrom )
		self.layersTo = preferences.IntPreference().getFromValue( 'Layers To (index):', 999999999 )
		self.archive.append( self.layersTo )
		self.perimeterWidthOverThickness = preferences.FloatPreference().getFromValue( 'Perimeter Width over Thickness (ratio):', 1.8 )
		self.archive.append( self.perimeterWidthOverThickness )
		#Create the archive, title of the execute button, title of the dialog & preferences fileName.
		self.executeTitle = 'Carve'
		self.saveTitle = 'Save Preferences'
		preferences.setHelpPreferencesFileNameTitleWindowPosition( self, 'skeinforge_tools.craft_plugins.carve.html' )

	def execute( self ):
		"Carve button has been clicked."
		fileNames = polyfile.getFileOrDirectoryTypes( self.fileNameInput.value, interpret.getImportPluginFilenames(), self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			writeOutput( fileName )


class CarveSkein:
	"A class to carve a GNU Triangulated Surface."
	def __init__( self ):
		self.margin = 20
		self.output = cStringIO.StringIO()
		self.textHeight = 22.5
		self.unitScale = 3.7

	def addInitializationToOutputSVG( self ):
		"Add initialization gcode to the output."
		endOfSVGHeaderIndex = self.svgTemplateLines.index( '//End of svg header' )
		self.addLines( self.svgTemplateLines[ : endOfSVGHeaderIndex ] )
		self.addLine( '\tdecimalPlacesCarried = ' + str( self.decimalPlacesCarried ) ) # Set decimal places carried.
		self.addLine( '\tlayerThickness = ' + self.getRounded( self.layerThickness ) ) # Set layer thickness.
		self.addLine( '\tperimeterWidth = ' + self.getRounded( self.perimeterWidth ) ) # Set perimeter width.
		self.addLine( '\tprocedureDone = "carve"' ) # The skein has been carved.
		self.addLine( '\textrusionStart = 1' ) # Initialization is finished, extrusion is starting.
		beginningOfPathSectionIndex = self.svgTemplateLines.index( '<!--Beginning of path section-->' )
		self.addLines( self.svgTemplateLines[ endOfSVGHeaderIndex + 1 : beginningOfPathSectionIndex ] )

	def addLayerStart( self, layerIndex, z ):
		"Add the start lines for the layer."
#		y = (1 * i + 1) * ( margin + sliceDimY * unitScale) + i * txtHeight
		layerTranslateY = layerIndex * self.textHeight + ( layerIndex + 1 ) * ( self.extent.y * self.unitScale + self.margin )
		zRounded = self.getRounded( z )
		self.addLine( '\t\t<g id="z %s" transform="translate(%s, %s)">' % ( zRounded, self.getRounded( self.margin ), self.getRounded( layerTranslateY ) ) )
		self.addLine( '\t\t\t<text y="15" fill="#000" stroke="none">Layer %s, z %s</text>' % ( layerIndex, zRounded ) )
#		<g id="z 0.1" transform="translate(20, 242)">
#			<text y="15" fill="#000" stroke="none">Layer 1, z 0.1</text>
#	unit scale (mm=3.7, in=96)
#	
#	g transform
#		x = margin
#		y = (layer + 1) * ( margin + (slice height * unit scale)) + (layer * 20)
#
#	text
#		y = text height
#
#	path transform
#		scale = (unit scale) (-1 * unitscale)
#		translate = (-1 * minX) (-1 * minY)

	def addLine( self, line ):
		"Add a line of text and a newline to the output."
		self.output.write( line + "\n" )

	def addLines( self, lines ):
		"Add lines of text to the output."
		for line in lines:
			self.addLine( line )

	def addRotatedLoopLayersToOutput( self, rotatedBoundaryLayers ):
		"Add rotated boundary layers to the output."
		truncatedRotatedBoundaryLayers = rotatedBoundaryLayers[ self.carvePreferences.layersFrom.value : self.carvePreferences.layersTo.value ]
		for truncatedRotatedBoundaryLayerIndex in xrange( len( truncatedRotatedBoundaryLayers ) ):
			truncatedRotatedBoundaryLayer = truncatedRotatedBoundaryLayers[ truncatedRotatedBoundaryLayerIndex ]
			self.addRotatedLoopLayerToOutput( truncatedRotatedBoundaryLayerIndex, truncatedRotatedBoundaryLayer )

	def addRotatedLoopLayerToOutput( self, layerIndex, rotatedBoundaryLayer ):
		"Add rotated boundary layer to the output."
		self.addLayerStart( layerIndex, rotatedBoundaryLayer.z )
		if rotatedBoundaryLayer.rotation != None:
			self.addLine('\t\t\t<!--bridgeDirection--> %s' % rotatedBoundaryLayer.rotation ) # Indicate the bridge direction.
#			<path transform="scale(3.7, -3.7) translate(0, 5)" d="M 0 -5 L 50 0 L60 50 L 5 50 z M 5 3 L5 15 L15 15 L15 5 z"/>
#		transform = 'scale(' + unitScale + ' ' + (unitScale * -1) + ') translate(' + (sliceMinX * -1) + ' ' + (sliceMinY * -1) + ')'
		pathString = '\t\t\t<path transform="scale(%s, %s) translate(%s, %s)" d="' % ( self.unitScale, - self.unitScale, self.getRounded( - self.cornerMinimum.x ), self.getRounded( - self.cornerMinimum.y ) )
		if len( rotatedBoundaryLayer.loops ) > 0:
			pathString += self.getSVGLoopString( rotatedBoundaryLayer.loops[ 0 ] )
		for loop in rotatedBoundaryLayer.loops[ 1 : ]:
			pathString += ' ' + self.getSVGLoopString( loop )
		pathString += '"/>'
		self.addLine( pathString )
		self.addLine( '\t\t</g>' )

	def addShutdownToOutput( self ):
		"Add shutdown svg to the output."
		endOfPathSectionIndex = self.svgTemplateLines.index( '<!--End of path section-->' )
		self.addLines( self.svgTemplateLines[ endOfPathSectionIndex + 1 : ] )

	def getReplacedSVGTemplateLines( self, fileName, rotatedBoundaryLayers ):
		"Get the lines of text from the svg_template.txt file."
#( layers.length + 1 ) * (margin + sliceDimY * unitScale + txtHeight) + margin + txtHeight + margin + 110
		svgTemplateText = gcodec.getFileTextInFileDirectory( __file__, 'svg_template.tmpl' )
		originalTextLines = gcodec.getTextLines( svgTemplateText )
		self.margin = getParameterFromJavascript( originalTextLines, 'margin', self.margin )
		self.textHeight = getParameterFromJavascript( originalTextLines, 'textHeight', self.textHeight )
		javascriptControlsWidth = getParameterFromJavascript( originalTextLines, 'javascripControlBoxX', 510.0 )
		noJavascriptControlsHeight = getParameterFromJavascript( originalTextLines, 'noJavascriptControlBoxY', 110.0 )
		controlTop = len( rotatedBoundaryLayers ) * ( self.margin + self.extent.y * self.unitScale + self.textHeight ) + 2.0 * self.margin + self.textHeight
#	width = margin + (sliceDimX * unitScale) + margin;
		svgTemplateText = getReplacedInQuotes( 'height', self.getRounded( controlTop + noJavascriptControlsHeight + self.margin ), svgTemplateText )
		width = 2.0 * self.margin + max( self.extent.y * self.unitScale, javascriptControlsWidth )
		svgTemplateText = getReplacedInQuotes( 'width', self.getRounded( width ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'layerThickness', self.getRounded( self.layerThickness ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'maxX', self.getRounded( self.cornerMaximum.x ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'minX', self.getRounded( self.cornerMinimum.x ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'dimX', self.getRounded( self.extent.x ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'maxY', self.getRounded( self.cornerMaximum.y ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'minY', self.getRounded( self.cornerMinimum.y ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'dimY', self.getRounded( self.extent.y ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'maxZ', self.getRounded( self.cornerMaximum.z ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'minZ', self.getRounded( self.cornerMinimum.z ), svgTemplateText )
		svgTemplateText = getReplacedWordAndInQuotes( 'dimZ', self.getRounded( self.extent.z ), svgTemplateText )
		summarizedFilename = gcodec.getSummarizedFilename( fileName ) + ' SVG Slice File'
		svgTemplateText = getReplacedWordAndInQuotes( 'Title', summarizedFilename, svgTemplateText )
		noJavascriptControlsTagString = '<g id="noJavascriptControls" fill="#000" transform="translate(%s, %s)">' % ( self.getRounded( self.margin ), self.getRounded( controlTop ) )
		svgTemplateText = getReplacedTagString( noJavascriptControlsTagString, 'noJavascriptControls', svgTemplateText )
#	<g id="noJavascriptControls" fill="#000" transform="translate(20, 1400)">
		return gcodec.getTextLines( svgTemplateText )

	def getRounded( self, number ):
		"Get number rounded to the number of carried decimal places as a string."
		return euclidean.getRoundedToDecimalPlacesString( self.decimalPlacesCarried, number )

	def getRoundedComplexString( self, point ):
		"Get the rounded complex string."
		return self.getRounded( point.real ) + ' ' + self.getRounded( point.imag )

	def getSVGLoopString( self, loop ):
		"Get the svg loop string."
		svgLoopString = ''
		if len( loop ) < 1:
			return ''
		oldRoundedComplexString = self.getRoundedComplexString( loop[ - 1 ] )
		for pointIndex in xrange( len( loop ) ):
			point = loop[ pointIndex ]
			stringBeginning = 'M '
			if len( svgLoopString ) > 0:
				stringBeginning = ' L '
			roundedComplexString = self.getRoundedComplexString( point )
			if roundedComplexString != oldRoundedComplexString:
				svgLoopString += stringBeginning + roundedComplexString
			oldRoundedComplexString = roundedComplexString
		if len( svgLoopString ) < 1:
			return ''
		return svgLoopString + ' z'

	def parseCarving( self, carvePreferences, carving, fileName ):
		"Parse gnu triangulated surface text and store the carved gcode."
		self.carvePreferences = carvePreferences
		self.layerThickness = carvePreferences.layerThickness.value
		self.setExtrusionDiameterWidth( carvePreferences )
		if carvePreferences.infillDirectionBridge.value:
			carving.setCarveBridgeLayerThickness( self.bridgeLayerThickness )
		carving.setCarveLayerThickness( self.layerThickness )
		importRadius = 0.5 * carvePreferences.importCoarseness.value * abs( self.perimeterWidth )
		carving.setCarveImportRadius( max( importRadius, 0.01 * self.layerThickness ) )
		carving.setCarveIsCorrectMesh( carvePreferences.correctMesh.value )
		rotatedBoundaryLayers = carving.getCarveRotatedBoundaryLayers()
		if len( rotatedBoundaryLayers ) < 1:
			return
		self.cornerMaximum = carving.getCarveCornerMaximum()
		self.cornerMinimum = carving.getCarveCornerMinimum()
		#reset from slicable
		self.layerThickness = carving.getCarveLayerThickness()
		self.setExtrusionDiameterWidth( carvePreferences )
		self.decimalPlacesCarried = int( max( 0.0, math.ceil( 1.0 - math.log10( self.layerThickness / carvePreferences.layerThicknessOverPrecision.value ) ) ) )
		self.extent = self.cornerMaximum - self.cornerMinimum
		self.svgTemplateLines = self.getReplacedSVGTemplateLines( fileName, rotatedBoundaryLayers )
		self.addInitializationToOutputSVG()
		self.addRotatedLoopLayersToOutput( rotatedBoundaryLayers )
		self.addShutdownToOutput()

	def setExtrusionDiameterWidth( self, carvePreferences ):
		"Set the extrusion diameter & width and the bridge thickness & width."
		self.bridgeLayerThickness = self.layerThickness * carvePreferences.infillBridgeThicknessOverLayerThickness.value
		self.perimeterWidth = carvePreferences.perimeterWidthOverThickness.value * self.layerThickness

def main():
	"Display the carve dialog."
	if len( sys.argv ) > 1:
		writeOutput( ' '.join( sys.argv[ 1 : ] ) )
	else:
		getDisplayedPreferences().root.mainloop()

if __name__ == "__main__":
	main()