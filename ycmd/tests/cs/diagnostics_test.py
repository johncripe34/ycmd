# Copyright (C) 2020 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

from hamcrest import ( assert_that, contains_exactly, contains_string, equal_to,
                       has_entries, has_entry, has_items )

from ycmd.tests.cs import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                            WrapOmniSharpServer, WaitUntilCsCompleterIsReady )
from ycmd.tests.test_utils import ( BuildRequest,
                                    LocationMatcher,
                                    RangeMatcher,
                                    StopCompleterServer,
                                    WithRetry )
from ycmd.utils import ReadFile


@WithRetry
@SharedYcmd
def Diagnostics_Basic_test( app ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               event_name = 'FileReadyToParse',
                               filetype = 'cs',
                               contents = contents )
    app.post_json( '/event_notification', event_data )

    diag_data = BuildRequest( filepath = filepath,
                              filetype = 'cs',
                              contents = contents,
                              line_num = 10,
                              column_num = 2 )

    results = app.post_json( '/detailed_diagnostic', diag_data ).json
    assert_that( results,
                 has_entry(
                     'message',
                     contains_string(
                       "Identifier expected" ) ) )


@SharedYcmd
def Diagnostics_ZeroBasedLineAndColumn_test( app ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               event_name = 'FileReadyToParse',
                               filetype = 'cs',
                               contents = contents )

    results = app.post_json( '/event_notification', event_data ).json

    assert_that( results, has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'text': contains_string( "Identifier expected" ),
        'location': LocationMatcher( filepath, 10, 12 ),
        'location_extent': RangeMatcher( filepath, ( 10, 12 ), ( 10, 12 ) ),
      } )
    ) )


@WithRetry
@SharedYcmd
def Diagnostics_WithRange_test( app ):
  filepath = PathToTestFile( 'testy', 'DiagnosticRange.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               event_name = 'FileReadyToParse',
                               filetype = 'cs',
                               contents = contents )

    results = app.post_json( '/event_notification', event_data ).json

    assert_that( results, has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'text': contains_string(
          "A namespace cannot directly "
          "contain members such as fields or methods" ),
        'location': LocationMatcher( filepath, 1, 1 ),
        'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 6 ) )
      } )
    ) )


@IsolatedYcmd()
def Diagnostics_MultipleSolution_test( app ):
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy', 'Program.cs' ) ]
  for filepath in filepaths:
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               event_name = 'FileReadyToParse',
                               filetype = 'cs',
                               contents = contents )

    results = app.post_json( '/event_notification', event_data ).json
    WaitUntilCsCompleterIsReady( app, filepath )

    event_data = BuildRequest( filepath = filepath,
                               event_name = 'FileReadyToParse',
                               filetype = 'cs',
                               contents = contents )

    results = app.post_json( '/event_notification', event_data ).json
    assert_that( results, has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'text': contains_string( "Identifier expected" ),
        'location': LocationMatcher( filepath, 10, 12 ),
        'location_extent': RangeMatcher(
            filepath, ( 10, 12 ), ( 10, 12 ) )
      } )
    ) )


@IsolatedYcmd( { 'max_diagnostics_to_display': 1 } )
def Diagnostics_MaximumDiagnosticsNumberExceeded_test( app ):
  filepath = PathToTestFile( 'testy', 'MaxDiagnostics.cs' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             event_name = 'FileReadyToParse',
                             filetype = 'cs',
                             contents = contents )

  app.post_json( '/event_notification', event_data ).json
  WaitUntilCsCompleterIsReady( app, filepath, False )

  event_data = BuildRequest( filepath = filepath,
                             event_name = 'FileReadyToParse',
                             filetype = 'cs',
                             contents = contents )

  results = app.post_json( '/event_notification', event_data ).json

  assert_that( results, contains_exactly(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'text': contains_string(
          "A namespace cannot directly "
          "contain members such as fields or methods" ),
      'location': LocationMatcher( filepath, 1, 1 ),
      'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 6 ) )
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'text': contains_string( 'Maximum number of diagnostics exceeded.' ),
      'location': LocationMatcher( filepath, 1, 1 ),
      'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ),
      'ranges': contains_exactly( RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ) )
    } )
  ) )

  StopCompleterServer( app, 'cs', filepath )
