"""
Comb is a script to comb the extrusion hair of a gcode file.

Comb bends the extruder travel paths around holes in the slice, to avoid stringers.  The default 'Activate Comb' checkbox is on.
When it's on the paths are bent.  When it is off, this script does nothing, the gcode text is handed over the next tool in the
skeinforge chain.  To run comb, in a shell type:
> python comb.py

The following examples comb the files Hollow Square.gcode & Hollow Square.gts.  The examples are run in a terminal in the folder
which contains Hollow Square.gcode, Hollow Square.gts and comb.py.  The comb function will comb if 'Activate Comb' is true, which
can be set in the dialog or by changing the preferences file 'comb.csv' in the '.skeinforge' folder in your home directory with a text
editor or a spreadsheet program set to separate tabs.  The functions writeOutput and getCombChainGcode check to see if the
text has been combed, if not they call getTowerChainGcode in tower.py to tower the text; once they have the towered text, then
they comb.


> python comb.py
This brings up the dialog, after clicking 'Comb', the following is printed:
File Hollow Square.gts is being chain combed.
The combed file is saved as Hollow Square_comb.gcode


>python
Python 2.5.1 (r251:54863, Sep 22 2007, 01:43:31)
[GCC 4.2.1 (SUSE Linux)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import comb
>>> comb.main()
This brings up the comb dialog.


>>> comb.writeOutput()
Hollow Square.gts
File Hollow Square.gts is being chain combed.
The combed file is saved as Hollow Square_comb.gcode


>>> comb.getCombGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")


>>> comb.getCombChainGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from skeinforge_tools.skeinforge_utilities.vec3 import Vec3
from skeinforge_tools.skeinforge_utilities import euclidean
from skeinforge_tools.skeinforge_utilities import gcodec
from skeinforge_tools.skeinforge_utilities import intercircle
from skeinforge_tools.skeinforge_utilities import preferences
from skeinforge_tools import analyze
from skeinforge_tools import import_translator
from skeinforge_tools import polyfile
from skeinforge_tools import tower
import cStringIO
import sys
import time


__author__ = "Enrique Perez (perez_enrique@yahoo.com)"
__date__ = "$Date: 2008/21/04 $"
__license__ = "GPL 3.0"

#maybe use 2d everywhere in case there is movement across layers
def getCombChainGcode( filename, gcodeText, combPreferences = None ):
	"Comb a gcode linear move text.  Chain comb the gcode if it is not already combed."
	gcodeText = gcodec.getGcodeFileText( filename, gcodeText )
	if not gcodec.isProcedureDone( gcodeText, 'tower' ):
		gcodeText = tower.getTowerChainGcode( filename, gcodeText )
	return getCombGcode( gcodeText, combPreferences )

def getCombGcode( gcodeText, combPreferences = None ):
	"Comb a gcode linear move text."
	if gcodeText == '':
		return ''
	if gcodec.isProcedureDone( gcodeText, 'comb' ):
		return gcodeText
	if combPreferences == None:
		combPreferences = CombPreferences()
		preferences.readPreferences( combPreferences )
	if not combPreferences.activateComb.value:
		return gcodeText
	skein = CombSkein()
	skein.parseGcode( gcodeText )
	return skein.output.getvalue()

def isLoopNumberEqual( betweenX, betweenXIndex, loopNumber ):
	"Determine if the loop number is equal."
	if betweenXIndex >= len( betweenX ):
		return False
	return betweenX[ betweenXIndex ].index == loopNumber

def writeOutput( filename = '' ):
	"Comb a gcode linear move file.  Chain comb the gcode if it is not already combed.  If no filename is specified, comb the first unmodified gcode file in this folder."
	if filename == '':
		unmodified = import_translator.getGNUTranslatorFilesUnmodified()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	combPreferences = CombPreferences()
	preferences.readPreferences( combPreferences )
	startTime = time.time()
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being chain combed.' )
	suffixFilename = filename[ : filename.rfind( '.' ) ] + '_comb.gcode'
	combGcode = getCombChainGcode( filename, '', combPreferences )
	if combGcode == '':
		return
	gcodec.writeFileText( suffixFilename, combGcode )
	print( 'The combed file is saved as ' + gcodec.getSummarizedFilename( suffixFilename ) )
	analyze.writeOutput( suffixFilename, combGcode )
	print( 'It took ' + str( int( round( time.time() - startTime ) ) ) + ' seconds to comb the file.' )

class CombSkein:
	"A class to comb a skein of extrusions."
	def __init__( self ):
		self.betweenTable = {}
		self.bridgeExtrusionWidthOverSolid = 1.0
		self.decimalPlacesCarried = 3
		self.extruderActive = False
		self.fillInset = 0.18
		self.layerFillInset = self.fillInset
		self.layer = None
		self.layers = []
		self.layerTable = {}
		self.layerZ = None
		self.lineIndex = 0
		self.lines = None
		self.loop = None
		self.oldLocation = None
		self.oldZ = None
		self.output = cStringIO.StringIO()
		self.pointTable = {}

	def addGcodeMovement( self, point ):
		"Add a movement to the output."
		self.addLine( "G1 X%s Y%s Z%s" % ( self.getRounded( point.x ), self.getRounded( point.y ), self.getRounded( point.z ) ) )

	def addIfTravel( self, splitLine ):
		"Add travel move around loops if this the extruder is off."
		location = gcodec.getLocationFromSplitLine( self.oldLocation, splitLine )
		if not self.extruderActive and self.oldLocation != None:
			self.insertPathsBetween( self.getOutloopLocation( location ), self.getOutloopLocation( self.oldLocation ) )
		self.oldLocation = location

	def addLine( self, line ):
		"Add a line of text and a newline to the output."
		self.output.write( line + "\n" )

	def addPathBetween( self, betweenFirst, betweenSecond, loopFirst ):
		"Add a path between the perimeter and the fill."
		clockwisePath = [ betweenFirst ]
		widdershinsPath = [ betweenFirst ]
		nearestFirstDistanceIndex = euclidean.getNearestDistanceSquaredIndex( betweenFirst, loopFirst )
		nearestSecondDistanceIndex = euclidean.getNearestDistanceSquaredIndex( betweenSecond, loopFirst )
		firstBeginIndex = ( int( nearestFirstDistanceIndex.imag ) + 1 ) % len( loopFirst )
		secondBeginIndex = ( int( nearestSecondDistanceIndex.imag ) + 1 ) % len( loopFirst )
		widdershinsLoop = euclidean.getAroundLoop( firstBeginIndex, secondBeginIndex, loopFirst )
		widdershinsPath += widdershinsLoop
		clockwiseLoop = euclidean.getAroundLoop( secondBeginIndex, firstBeginIndex, loopFirst )
		clockwiseLoop.reverse()
		clockwisePath += clockwiseLoop
		clockwisePath.append( betweenSecond )
		widdershinsPath.append( betweenSecond )
		if euclidean.getPathLength( widdershinsPath ) > euclidean.getPathLength( clockwisePath ):
			widdershinsPath = clockwisePath
		widdershinsPath = euclidean.getAwayPath( widdershinsPath, 0.2 * self.layerFillInset )
		for point in widdershinsPath:
			self.addGcodeMovement( point )

	def addToLoop( self, location ):
		"Add a location to loop."
		if self.layer == None:
			if not self.oldZ in self.layerTable:
				self.layerTable[ self.oldZ ] = []
			self.layer = self.layerTable[ self.oldZ ]
		if self.loop == None:
			self.loop = [] #starting with an empty array because a closed loop does not have to restate its beginning
			self.layer.append( self.loop )
		if self.loop != None:
			self.loop.append( location )
			self.pointTable[ str( location ) ] = True

	def getBetweens( self ):
		"Set betweens for the layer."
		if self.layerZ in self.betweenTable:
			return self.betweenTable[ self.layerZ ]
		halfFillInset = 0.5 * self.layerFillInset
		betweens = []
		for loop in self.layerTable[ self.layerZ ]:
			circleNodes = intercircle.getCircleNodesFromLoop( loop, self.layerFillInset )
			centers = intercircle.getCentersFromCircleNodes( circleNodes )
			for center in centers:
				inset = intercircle.getInsetFromClockwiseLoop( center, halfFillInset )
				if euclidean.isLargeSameDirection( inset, center, self.layerFillInset ):
					if euclidean.isPathInsideLoop( loop, inset ) != euclidean.isWiddershins( loop ):
						betweens.append( inset )
		self.betweenTable[ self.layerZ ] = betweens
		return betweens

	def getOutloopLocation( self, point ):
		"Get location outside of loop."
		if str( point ) not in self.pointTable:
			return point
		closestBetween = None
		closestDistanceSquaredIndex = complex( 999999999999999999.0, - 1 )
		for between in self.getBetweens():
			distanceSquaredIndex = euclidean.getNearestDistanceSquaredIndex( point, between )
			if distanceSquaredIndex.real < closestDistanceSquaredIndex.real:
				closestBetween = between
				closestDistanceSquaredIndex = distanceSquaredIndex
		if closestBetween == None:
			print( 'This should never happen, closestBetween should always exist.' )
			return point
		closestIndex = int( round( closestDistanceSquaredIndex.imag ) )
		segmentBegin = closestBetween[ closestIndex ]
		segmentEnd = closestBetween[ ( closestIndex + 1 ) % len( closestBetween ) ]
		nearestPoint = euclidean.getNearestPointOnSegment( segmentBegin, segmentEnd, point )
		distanceToNearestPoint = point.distance( nearestPoint )
		nearestMinusOld = nearestPoint.minus( point )
		nearestMinusOld.scale( 1.5 )
		return point.plus( nearestMinusOld )

	def getRounded( self, number ):
		"Get number rounded to the number of carried decimal places as a string."
		return euclidean.getRoundedToDecimalPlaces( self.decimalPlacesCarried, number )

	def insertPathsBetween( self, nextBeginning, pathEnd ):
		"Insert paths between the perimeter and the fill."
		betweenX = []
		switchX = []
		segment = nextBeginning.minus( pathEnd )
		segment.normalize()
		segmentXY = segment.dropAxis( 2 )
		segmentYMirror = complex( segment.x, - segment.y )
		pathEndRotated = euclidean.getRoundZAxisByPlaneAngle( segmentYMirror, pathEnd )
		nextBeginningRotated = euclidean.getRoundZAxisByPlaneAngle( segmentYMirror, nextBeginning )
		y = pathEndRotated.y
		z = pathEndRotated.z
		for betweenIndex in range( len( self.getBetweens() ) ):
			between = self.getBetweens()[ betweenIndex ]
			betweenRotated = euclidean.getPathRoundZAxisByPlaneAngle( segmentYMirror, between )
			euclidean.addXIntersections( betweenRotated, betweenIndex, switchX, y )
		switchX.sort()
		maximumX = max( pathEndRotated.x, nextBeginningRotated.x )
		minimumX = min( pathEndRotated.x, nextBeginningRotated.x )
		for xIntersection in switchX:
			if xIntersection.x > minimumX and xIntersection.x < maximumX:
				betweenX.append( xIntersection )
		betweenXIndex = 0
		while betweenXIndex < len( betweenX ) - 1:
			betweenXFirst = betweenX[ betweenXIndex ]
			betweenXSecond = betweenX[ betweenXIndex + 1 ]
			if betweenXSecond.index == betweenXFirst.index:
				betweenXIndex += 1
				betweenFirst = euclidean.getRoundZAxisByPlaneAngle( segmentXY, Vec3( betweenXFirst.x, y, z ) )
				betweenSecond = euclidean.getRoundZAxisByPlaneAngle( segmentXY, Vec3( betweenXSecond.x, y, z ) )
				loopFirst = self.getBetweens()[ betweenXFirst.index ]
				self.addPathBetween( betweenFirst, betweenSecond, loopFirst )
			betweenXIndex += 1

	def parseGcode( self, gcodeText ):
		"Parse gcode text and store the comb gcode."
		self.lines = gcodec.getTextLines( gcodeText )
		for line in self.lines:
			self.parseLine( line )
		self.oldLocation = None
		for lineIndex in range( len( self.lines ) ):
			line = self.lines[ lineIndex ]
			self.parseAddTravel( line )

	def parseLine( self, line ):
		"Parse a gcode line."
		splitLine = line.split()
		if len( splitLine ) < 1:
			return
		firstWord = splitLine[ 0 ]
		if firstWord == 'M103':
			self.loop = None
		elif firstWord == '(<bridgeExtrusionWidthOverSolid>':
			self.bridgeExtrusionWidthOverSolid = float( splitLine[ 1 ] )
		elif firstWord == '(<boundaryPoint>':
			location = gcodec.getLocationFromSplitLine( None, splitLine )
			self.addToLoop( location )
		elif firstWord == '(<decimalPlacesCarried>':
			self.decimalPlacesCarried = int( splitLine[ 1 ] )
		elif firstWord == '(<layerStart>':
			self.layer = None
			self.loop = None
			self.oldZ = float( splitLine[ 1 ] )
		elif firstWord == '(<fillInset>':
			self.fillInset = float( splitLine[ 1 ] )

	def parseAddTravel( self, line ):
		"Parse a gcode line and add it to the comb skein."
		splitLine = line.split()
		if len( splitLine ) < 1:
			return
		firstWord = splitLine[ 0 ]
		if firstWord == 'G1':
			self.addIfTravel( splitLine )
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
		elif firstWord == '(<extrusionStart>':
			self.addLine( '(<procedureDone> comb )' )
		elif firstWord == '(<layerStart>':
			self.layerFillInset = self.fillInset
			self.layerZ = float( splitLine[ 1 ] )
		elif firstWord == '(<bridgeLayer>':
			self.layerFillInset = self.fillInset * self.bridgeExtrusionWidthOverSolid
		self.addLine( line )


class CombPreferences:
	"A class to handle the comb preferences."
	def __init__( self ):
		"Set the default preferences, execute title & preferences filename."
		#Set the default preferences.
		self.archive = []
		self.activateComb = preferences.BooleanPreference().getFromValue( 'Activate Comb', True )
		self.archive.append( self.activateComb )
		self.filenameInput = preferences.Filename().getFromFilename( import_translator.getGNUTranslatorGcodeFileTypeTuples(), 'Open File to be Combed', '' )
		self.archive.append( self.filenameInput )
		#Create the archive, title of the execute button, title of the dialog & preferences filename.
		self.executeTitle = 'Comb'
		self.filenamePreferences = preferences.getPreferencesFilePath( 'comb.csv' )
		self.filenameHelp = 'skeinforge_tools.comb.html'
		self.saveTitle = 'Save Preferences'
		self.title = 'Comb Preferences'

	def execute( self ):
		"Comb button has been clicked."
		filenames = polyfile.getFileOrDirectoryTypesUnmodifiedGcode( self.filenameInput.value, import_translator.getGNUTranslatorFileTypes(), self.filenameInput.wasCancelled )
		for filename in filenames:
			writeOutput( filename )


def main( hashtable = None ):
	"Display the comb dialog."
	if len( sys.argv ) > 1:
		writeOutput( ' '.join( sys.argv[ 1 : ] ) )
	else:
		preferences.displayDialog( CombPreferences() )

if __name__ == "__main__":
	main()
