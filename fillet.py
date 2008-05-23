"""
Fillet is a script to fillet or bevel the corners on a gcode file.

To run fillet, install python 2.x on your machine, which is avaliable from http://www.python.org/download/

To use the preferences dialog you'll also need Tkinter, which probably came with the python installation.  If it did not, look for it at:
www.tcl.tk/software/tcltk/

To export a GNU Triangulated Surface file from Art of Illusion, you can use the Export GNU Triangulated Surface script at:
http://members.axion.net/~enrique/Export%20GNU%20Triangulated%20Surface.bsh

To bring it into Art of Illusion, drop it into the folder ArtOfIllusion/Scripts/Tools/.

The GNU Triangulated Surface format is supported by Mesh Viewer, and it is described at:
http://gts.sourceforge.net/reference/gts-surfaces.html#GTS-SURFACE-WRITE

To turn an STL file into filled, filleted gcode, first import the file using the STL import plugin in the import submenu of the file menu
of Art of Illusion.  Then from the Scripts submenu in the Tools menu, choose Export GNU Triangulated Surface and select the
imported STL shape.  Then type 'python slice.py' in a shell in the folder which slice & fillet are in and when the dialog pops up, set
the parameters and click 'Save Preferences'.  Then type 'python fill.py' in a shell in the folder which fill is in and when the dialog
pops up, set the parameters and click 'Save Preferences'.  Then type 'python comb.py' in a shell in the folder which fill is in and when the dialog
pops up, change the parameters if you wish but the default 'Comb Hair' is fine.  Then type 'python fillet.py' in a shell and when the dialog pops up,
change the parameters if you wish but the default bevel is fine.  Then click 'Fillet', choose the file which you exported in
Export GNU Triangulated Surface and the filled & filleted file will be saved with the suffix '_fillet'.

To write documentation for this program, open a shell in the fillet.py directory, then type 'pydoc -w fillet', then open 'fillet.html' in
a browser or click on the '?' button in the dialog.  To use other functions of fillet, type 'python' in a shell to run the python interpreter,
then type 'import fillet' to import this program.

The computation intensive python modules will use psyco if it is available and run about twice as fast.  Psyco is described at:
http://psyco.sourceforge.net/index.html

The psyco download page is:
http://psyco.sourceforge.net/download.html

The following examples fillet the files Hollow Square.gcode & Hollow Square.gts.  The examples are run in a terminal in the folder which contains
Hollow Square.gcode, Hollow Square.gts and fillet.py.  The fillet function executes the preferred fillet type, which can be set in the dialog or by changing
the preferences file 'fillet.csv' with a text editor or a spreadsheet program set to separate tabs.  The functions filletChainFile and
getFilletChainGcode check to see if the text has been combed, if not they call the getCombChainGcode in comb.py to fill the text; once they
have the combed text, then they fillet.


> pydoc -w fillet
wrote fillet.html


> python fillet.py
This brings up the dialog, after clicking 'Fillet', the following is printed:
File Hollow Square.gts is being chain filleted.
The filleted file is saved as Hollow Square_fillet.gcode


>python
Python 2.5.1 (r251:54863, Sep 22 2007, 01:43:31)
[GCC 4.2.1 (SUSE Linux)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import fillet
>>> fillet.main()
This brings up the fillet dialog.


>>> fillet.arcPointFile()
File Hollow Square.gcode is being filleted into arc points.
The arc point file is saved as Hollow Square_fillet.gcode


>>> fillet.arcRadiusFile()
File Hollow Square.gcode is being filleted into arc radiuses.
The arc radius file is saved as Hollow Square_fillet.gcode


>>> fillet.arcSegmentFile()
File Hollow Square.gcode is being arc segmented.
The arc segment file is saved as Hollow Square_fillet.gcode


>>> fillet.bevelFile()
File Hollow Square.gcode is being beveled.
The beveled file is saved as Hollow Square_fillet.gcode


>>> fillet.filletChainFile()
Hollow Square.gts
File Hollow Square.gcode is being chain filleted.
The filleted file is saved as Hollow Square_fillet.gcode


>>> fillet.filletFile()
File Hollow Square.gcode is being filleted.
The filleted file is saved as Hollow Square_fillet.gcode


>>> fillet.getArcPointGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")


>>> fillet.getArcRadiusGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")


>>> fillet.getArcSegmentGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")


>>> fillet.getBevelGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")


>>> fillet.getFilletGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")


>>> fillet.getFilletChainGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")

"""

from vec3 import Vec3
import comb
import cStringIO
import euclidean
import gcodec
import preferences
import time
import vectorwrite


__author__ = "Enrique Perez (perez_enrique@yahoo.com)"
__date__ = "$Date: 2008/21/04 $"
__license__ = "GPL 3.0"


def arcPointFile( filename = '' ):
	"Fillet a gcode linear move file into a helical point move file.  If no filename is specified, arc point the first unmodified gcode file in this folder."
	if filename == '':
		unmodified = gcodec.getUnmodifiedGCodeFiles()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	filletPreferences = FilletPreferences()
	preferences.readPreferences( filletPreferences )
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being filleted into arc points.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	gcodec.writeFileMessageSuffix( filename, getArcPointGcode( filletPreferences, gcodeText ), 'The arc point file is saved as ', '_fillet' )

def arcRadiusFile( filename = '' ):
	"Fillet a gcode linear move file into a helical radius move file.  If no filename is specified, arc radius the first unmodified gcode file in this folder."
	if filename == '':
		unmodified = gcodec.getUnmodifiedGCodeFiles()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	filletPreferences = FilletPreferences()
	preferences.readPreferences( filletPreferences )
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being filleted into arc radiuses.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	gcodec.writeFileMessageSuffix( filename, getArcRadiusGcode( filletPreferences, gcodeText ), 'The arc radius file is saved as ', '_fillet' )

def arcSegmentFile( filename = '' ):
	"Fillet a gcode linear move file into an arc segment linear move file.  If no filename is specified, arc segment the first unmodified gcode file in this folder."
	if filename == '':
		unmodified = gcodec.getUnmodifiedGCodeFiles()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	filletPreferences = FilletPreferences()
	preferences.readPreferences( filletPreferences )
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being arc segmented.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	gcodec.writeFileMessageSuffix( filename, getArcSegmentGcode( filletPreferences, gcodeText ), 'The arc segment file is saved as ', '_fillet' )

def bevelFile( filename = '' ):
	"Bevel a gcode linear move file.  If no filename is specified, bevel the first unmodified gcode file in this folder."
	if filename == '':
		unmodified = gcodec.getUnmodifiedGCodeFiles()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	filletPreferences = FilletPreferences()
	preferences.readPreferences( filletPreferences )
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being beveled.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	gcodec.writeFileMessageSuffix( filename, getBevelGcode( filletPreferences, gcodeText ), 'The beveled file is saved as ', '_fillet' )

def filletChainFile( filename = '' ):
	"""Fillet a gcode linear move file.  Chain fill the gcode if it is not already filled.
	Depending on the preferences, either arcPoint, arcRadius, arcSegment, bevel or do nothing.
	If no filename is specified, fillet the first unmodified gcode file in this folder."""
	if filename == '':
		unmodified = gcodec.getGNUGcode()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	filletPreferences = FilletPreferences()
	preferences.readPreferences( filletPreferences )
	startTime = time.time()
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being chain filleted.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	suffixFilename = filename[ : filename.rfind( '.' ) ] + '_fillet.gcode'
	gcodec.writeFileText( suffixFilename, getFilletChainGcode( gcodeText, filletPreferences ) )
	print( 'The filleted file is saved as ' + gcodec.getSummarizedFilename( suffixFilename ) )
	if filletPreferences.writeSVG.value:
		vectorwrite.writeVectorFile( suffixFilename )
	print( 'It took ' + str( int( round( time.time() - startTime ) ) ) + ' seconds to fillet the file.' )

def filletFile( filename = '' ):
	"""Fillet a gcode linear move file.  Depending on the preferences, either arcPoint, arcRadius, arcSegment, bevel or do nothing.
	If no filename is specified, fillet the first unmodified gcode file in this folder."""
	if filename == '':
		unmodified = gcodec.getUnmodifiedGCodeFiles()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	filletPreferences = FilletPreferences()
	preferences.readPreferences( filletPreferences )
	if filletPreferences.doNotFillet.value:
		print( 'The preference is to not fillet, so nothing will be done.' )
		return
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being filleted.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	suffixFilename = filename[ : filename.rfind( '.' ) ] + '_fillet.gcode'
	gcodec.writeFileText( suffixFilename, getFilletGcode( gcodeText, filletPreferences ) )
	print( 'The filleted file is saved as ' + suffixFilename )
	if filletPreferences.writeSVG.value:
		vectorwrite.writeVectorFile( suffixFilename )

def getArcPointGcode( filletPreferences, gcodeText ):
	"Arc point a gcode linear move text into a helical point move gcode text."
	skein = ArcPointSkein()
	skein.parseGcode( filletPreferences, gcodeText )
	return skein.output.getvalue()

def getArcRadiusGcode( filletPreferences, gcodeText ):
	"Arc radius a gcode linear move text into a helical radius move gcode text."
	skein = ArcRadiusSkein()
	skein.parseGcode( filletPreferences, gcodeText )
	return skein.output.getvalue()

def getArcSegmentGcode( filletPreferences, gcodeText ):
	"Arc segment a gcode linear move text into an arc segment linear move gcode text."
	skein = ArcSegmentSkein()
	skein.parseGcode( filletPreferences, gcodeText )
	return skein.output.getvalue()

def getBevelGcode( filletPreferences, gcodeText ):
	"Bevel a gcode linear move text."
	skein = BevelSkein()
	skein.parseGcode( filletPreferences, gcodeText )
	return skein.output.getvalue()

def getFilletChainGcode( gcodeText, filletPreferences = None ):
	"Fillet a gcode linear move text.  Chain comb the gcode if it is not already combed."
	if not gcodec.isProcedureDone( gcodeText, 'comb' ):
		gcodeText = comb.getCombChainGcode( gcodeText )
	return getFilletGcode( gcodeText, filletPreferences )

def getFilletGcode( gcodeText, filletPreferences = None ):
	"Fillet a gcode linear move text."
	if gcodeText == '':
		return ''
	if gcodec.isProcedureDone( gcodeText, 'fillet' ):
		return gcodeText
	if filletPreferences == None:
		filletPreferences = FilletPreferences()
		preferences.readPreferences( filletPreferences )
	if filletPreferences.arcPoint.value:
		return getArcPointGcode( filletPreferences, gcodeText )
	elif filletPreferences.arcRadius.value:
		return getArcRadiusGcode( filletPreferences, gcodeText )
	elif filletPreferences.arcSegment.value:
		return getArcSegmentGcode( filletPreferences, gcodeText )
	elif filletPreferences.bevel.value:
		return getBevelGcode( filletPreferences, gcodeText )
	return gcodeText

class BevelSkein:
	"A class to bevel a skein of extrusions."
	def __init__( self ):
		self.extruderActive = False
		self.feedrateMinute = 600.0
		self.halfExtrusionWidth = 0.2
		self.lineIndex = 0
		self.lines = None
		self.oldActiveLocation = None
		self.oldLocation = None
		self.output = cStringIO.StringIO()
		self.shouldAddLine = True

	def addFeedrateEnd( self ):
		"Add the gcode feedrate and a newline to the output."
		self.addLine(  ' F' + euclidean.getRoundedToThreePlaces( self.feedrateMinute ) )

	def addLine( self, line ):
		"Add a line of text and a newline to the output."
		self.output.write( line + '\n' )

	def addLinearMovePoint( self, point ):
		"Add a gcode linear move, feedrate and newline to the output."
		self.output.write( 'G1' )
		self.addPoint( point )
		self.addFeedrateEnd()

	def addPoint( self, point ):
		"Add a gcode point to the output."
		self.output.write( ' X' + euclidean.getRoundedToThreePlaces( point.x ) + ' Y' + euclidean.getRoundedToThreePlaces( point.y ) + ' Z' + euclidean.getRoundedToThreePlaces( point.z ) )

	def getNextActive( self ):
		"Get the next linear move where the extruder is still active.  Return none is none is found."
		for afterIndex in range( self.lineIndex + 1, len( self.lines ) ):
			line = self.lines[ afterIndex ]
			splitLine = line.split( ' ' )
			firstWord = "";
			if len( splitLine ) > 0:
				firstWord = splitLine[ 0 ]
			if firstWord == 'G1':
				nextActive = gcodec.getLocationFromSplitLine( self.oldLocation, splitLine )
				return nextActive
			if firstWord == 'M103':
				return None
		return None

	def linearMove( self, splitLine ):
		"Bevel a linear move."
		location = gcodec.getLocationFromSplitLine( self.oldLocation, splitLine )
		indexOfF = gcodec.indexOfStartingWithSecond( "F", splitLine )
		if indexOfF > 0:
			self.feedrateMinute = gcodec.getDoubleAfterFirstLetter( splitLine[ indexOfF ] )
		if not self.extruderActive:
			return
		if self.oldActiveLocation != None:
			nextActive = self.getNextActive()
			if nextActive != None:
				self.shouldAddLine = False
				location = self.splitPointGetAfter( location, nextActive, self.oldActiveLocation )
		self.oldActiveLocation = location

	def parseGcode( self, filletPreferences, gcodeText ):
		"Parse gcode text and store the bevel gcode."
		self.lines = gcodec.getTextLines( gcodeText )
		self.parseInitialization( filletPreferences )
		for self.lineIndex in range( self.lineIndex, len( self.lines ) ):
			line = self.lines[ self.lineIndex ]
			self.parseLine( line )

	def parseInitialization( self, filletPreferences ):
		"Parse gcode initialization and store the parameters."
		for self.lineIndex in range( len( self.lines ) ):
			line = self.lines[ self.lineIndex ]
			splitLine = line.split( ' ' )
			firstWord = ''
			if len( splitLine ) > 0:
				firstWord = splitLine[ 0 ]
			if firstWord == 'M109':
				self.halfExtrusionWidth = 0.5 * gcodec.getDoubleAfterFirstLetter( splitLine[ 1 ] ) * filletPreferences.filletRadiusOverHalfExtrusionWidth.value
			elif firstWord == 'M112':
				self.addLine( 'M111 (fillet)' )
				return
			self.addLine( line )

	def parseLine( self, line ):
		"Parse a gcode line and add it to the bevel gcode."
		self.shouldAddLine = True
		splitLine = line.split( ' ' )
		if len( splitLine ) < 1:
			return 0
		firstWord = splitLine[ 0 ]
		if firstWord == 'G1':
			self.linearMove( splitLine )
		if firstWord == 'M101':
			self.extruderActive = True
		if firstWord == 'M103':
			self.extruderActive = False
			self.oldActiveLocation = None
		if self.shouldAddLine:
			self.addLine( line )

	def splitPointGetAfter( self, location, nextActive, oldActiveLocation ):
		"Bevel a point and return the end of the bevel."
		bevelLength = 0.5 * self.halfExtrusionWidth
		beforeSegment = oldActiveLocation.minus( location )
		beforeSegmentLength = beforeSegment.length()
		if beforeSegmentLength == 0.0:
			self.shouldAddLine = True
			return location
		afterSegment = nextActive.minus( location )
		afterSegmentExtension = 0.5 * afterSegment.length()
		if afterSegmentExtension == 0.0:
			self.shouldAddLine = True
			return location
		bevelLength = min( afterSegmentExtension, bevelLength )
		if beforeSegmentLength < bevelLength:
			bevelLength = beforeSegmentLength
		else:
			beforePoint = euclidean.getPointPlusSegmentWithLength( bevelLength, location, beforeSegment )
			self.addLinearMovePoint( beforePoint )
		afterPoint = euclidean.getPointPlusSegmentWithLength( bevelLength, location, afterSegment )
		self.addLinearMovePoint( afterPoint )
		return afterPoint


class ArcSegmentSkein( BevelSkein ):
	"A class to arc segment a skein of extrusions."
	def addArc( self, afterCenterDifferenceAngle, afterPoint, beforeCenterSegment, beforePoint, center ):
		"Add arc segments to the filleted skein."
		curveSection = 0.5
		absoluteDifferenceAngle = abs( afterCenterDifferenceAngle )
		steps = int( math.ceil( max( absoluteDifferenceAngle * 2.4, absoluteDifferenceAngle * beforeCenterSegment.length() / curveSection ) ) )
		stepPlaneAngle = euclidean.getPolar( afterCenterDifferenceAngle / steps, 1.0 )
		for step in range( 1, steps ):
			beforeCenterSegment = euclidean.getRoundZAxisByPlaneAngle( stepPlaneAngle, beforeCenterSegment )
			arcPoint = center.plus( beforeCenterSegment )
			self.addLinearMovePoint( arcPoint )
		self.addLinearMovePoint( afterPoint )

	def splitPointGetAfter( self, location, nextActive, oldActiveLocation ):
		"Fillet a point into arc segments and return the end of the last segment."
		afterSegment = nextActive.minus( location )
		afterSegmentLength = afterSegment.length()
		afterSegmentExtension = 0.5 * afterSegmentLength
		if afterSegmentExtension == 0.0:
			self.shouldAddLine = True
			return location
		beforeSegment = oldActiveLocation.minus( location )
		beforeSegmentLength = beforeSegment.length()
		if beforeSegmentLength == 0.0:
			self.shouldAddLine = True
			return location
		radius = self.halfExtrusionWidth
		afterSegmentNormalized = afterSegment.times( 1.0 / afterSegmentLength )
		beforeSegmentNormalized = beforeSegment.times( 1.0 / beforeSegmentLength )
		betweenCenterDotNormalized = afterSegmentNormalized.plus( beforeSegmentNormalized )
		if betweenCenterDotNormalized.length() < 0.01 * self.halfExtrusionWidth:
			self.shouldAddLine = True
			return location
		betweenCenterDotNormalized.normalize()
		beforeSegmentNormalizedWiddershins = euclidean.getRotatedWiddershinsQuarterAroundZAxis( beforeSegmentNormalized )
		betweenAfterPlaneDot = abs( euclidean.getPlaneDot( betweenCenterDotNormalized, beforeSegmentNormalizedWiddershins ) )
		centerDotDistance = radius / betweenAfterPlaneDot
		bevelLength = math.sqrt( centerDotDistance * centerDotDistance - radius * radius )
		radiusOverBevelLength = radius / bevelLength
		bevelLength = min( bevelLength, radius )
		bevelLength = min( afterSegmentExtension, bevelLength )
		beforePoint = oldActiveLocation
		if beforeSegmentLength < bevelLength:
			bevelLength = beforeSegmentLength
		else:
			beforePoint = euclidean.getPointPlusSegmentWithLength( bevelLength, location, beforeSegment )
			self.addLinearMovePoint( beforePoint )
		afterPoint = euclidean.getPointPlusSegmentWithLength( bevelLength, location, afterSegment )
		radius = bevelLength * radiusOverBevelLength
		centerDotDistance = radius / betweenAfterPlaneDot
		center = location.plus( betweenCenterDotNormalized.times( centerDotDistance ) )
		afterCenterSegment = afterPoint.minus( center )
		beforeCenterSegment = beforePoint.minus( center )
		afterCenterDifferenceAngle = euclidean.getAngleAroundZAxisDifference( afterCenterSegment, beforeCenterSegment )
		self.addArc( afterCenterDifferenceAngle, afterPoint, beforeCenterSegment, beforePoint, center )
		return afterPoint


class ArcPointSkein( ArcSegmentSkein ):
	"A class to arc point a skein of extrusions."
	def addArc( self, afterCenterDifferenceAngle, afterPoint, beforeCenterSegment, beforePoint, center ):
		"Add an arc point to the filleted skein."
		afterPointMinusBefore = afterPoint.minus( beforePoint )
		centerMinusBefore = center.minus( beforePoint )
		if afterCenterDifferenceAngle > 0.0:
			self.output.write( 'G3' )
		else:
			self.output.write( 'G2' )
		self.addPoint( afterPointMinusBefore )
		self.addRelativeCenter( centerMinusBefore )
		self.addFeedrateEnd()

	def addRelativeCenter( self, centerMinusBefore ):
		"Add the relative center to a line of the arc point filleted skein."
		self.output.write( ' I' + euclidean.getRoundedToThreePlaces( centerMinusBefore.x ) + ' J' + euclidean.getRoundedToThreePlaces( centerMinusBefore.y ) )


class ArcRadiusSkein( ArcPointSkein ):
	"A class to arc radius a skein of extrusions."
	def addRelativeCenter( self, centerMinusBefore ):
		"Add the relative center to a line of the arc radius filleted skein."
		planeCenterMinusBefore = centerMinusBefore.dropAxis( 2 )
		radius = abs( planeCenterMinusBefore )
		self.output.write( ' R' + euclidean.getRoundedToThreePlaces( radius ) )


class FilletPreferences:
	"A class to handle the fillet preferences."
	def __init__( self ):
		"Set the default preferences, execute title & preferences filename."
		#Set the default preferences.
		filletRadio = []
		self.arcPoint = preferences.RadioLabel().getFromRadioLabel( 'Arc Point', 'Fillet Procedure Choice:', filletRadio, False )
		self.arcRadius = preferences.Radio().getFromRadio( 'Arc Radius', filletRadio, False )
		self.arcSegment = preferences.Radio().getFromRadio( 'Arc Segment', filletRadio, False )
		self.bevel = preferences.Radio().getFromRadio( 'Bevel', filletRadio, True )
		self.doNotFillet = preferences.Radio().getFromRadio( 'Do Not Fillet', filletRadio, False )
		self.filletRadiusOverHalfExtrusionWidth = preferences.FloatPreference().getFromValue( 'Fillet Radius Over Half Extrusion Width (ratio):', 0.7 )
		self.writeSVG = preferences.BooleanPreference().getFromValue( 'Write Scalable Vector Graphics:', True )
		directoryRadio = []
		self.directoryPreference = preferences.RadioLabel().getFromRadioLabel( 'Fillet All Unmodified Files in a Directory', 'File or Directory Choice:', directoryRadio, False )
		self.filePreference = preferences.Radio().getFromRadio( 'Fillet File', directoryRadio, True )
		self.filenameInput = preferences.Filename().getFromFilename( [ ( 'GNU Triangulated Surface text files', '*.gts' ), ( 'Gcode text files', '*.gcode' ) ], 'Open File to be Filleted', '' )
		#Create the archive, title of the execute button, title of the dialog & preferences filename.
		self.archive = [
			self.arcPoint,
			self.arcRadius,
			self.arcSegment,
			self.bevel,
			self.doNotFillet,
			self.filletRadiusOverHalfExtrusionWidth,
			self.writeSVG,
			self.directoryPreference,
			self.filePreference,
			self.filenameInput ]
		self.executeTitle = 'Fillet'
#		self.filename = getPreferencesFilePath( 'fillet.csv' )
		self.filenamePreferences = 'fillet.csv'
		self.filenameHelp = 'fillet.html'
		self.title = 'Fillet Preferences'

	def execute( self ):
		"Fillet button has been clicked."
		filenames = gcodec.getGcodeDirectoryOrFile( self.directoryPreference.value, self.filenameInput.value, self.filenameInput.wasCancelled )
		for filename in filenames:
			filletChainFile( filename )


def main( hashtable = None ):
	"Display the fillet dialog."
	preferences.displayDialog( FilletPreferences() )

if __name__ == "__main__":
	main()