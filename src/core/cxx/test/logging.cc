/**
 * @file core/cxx/test/logging.cc
 * @date Tue Jan 18 17:07:26 2011 +0100
 * @author André Anjos <andre.anjos@idiap.ch>
 *
 * @brief Multiple C++ tests for the logging infrastructure.
 *
 * Copyright (C) 2011-2013 Idiap Research Institute, Martigny, Switzerland
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3 of the License.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#define BOOST_TEST_DYN_LINK
#define BOOST_TEST_MODULE Logging Tests
#define BOOST_TEST_MAIN
#include <boost/test/unit_test.hpp>
#include <boost/filesystem.hpp>
#include <boost/shared_array.hpp>
#include <boost/iostreams/filtering_stream.hpp>
#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/copy.hpp>

#include <bob/core/logging.h>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <iostream>
#include <fstream>

using namespace bob::core;

//tests if the streams are correctly initialized and will work correctly
BOOST_AUTO_TEST_CASE( test_basic )
{
  TDEBUG1("NOT SUPPOSED TO BE PRINTED!");
# if defined(_WIN32)
  putenv("BOB_DEBUG=3");
# else
  setenv("BOB_DEBUG", "3", 1); ///< after this, all messages should be printed
# endif
  TDEBUG1("This is a debug message, level 1. " << "I can also stream!");
  TDEBUG2("This is a debug message, level 2. ");
  TDEBUG3("This is a debug message, level 3. ");
  info << "This is an info message." << std::endl;
  warn << "This is a warning message." << std::endl;
  error << "This is an error message." << std::endl;
# if defined(_WIN32)
  putenv("BOB_DEBUG=");
# else
  unsetenv("BOB_DEBUG");
# endif
}

/**
 * Returns the contents of a file in a single string. Useful for testing the
 * output of logging.
 */
std::string get_contents(const std::string& fname) {
  std::ifstream file(fname.c_str(), std::ios_base::in | std::ios_base::binary);
  std::ostringstream retval;
  if (boost::filesystem::path(fname).extension() == ".gz") {
    boost::iostreams::filtering_istream in;
    in.push(boost::iostreams::gzip_decompressor());
    in.push(file);
    boost::iostreams::copy(in, retval);
  }
  else {
    boost::iostreams::copy(file, retval);
  }
  return retval.str();
}

//tests if I can easily switch streams 
BOOST_AUTO_TEST_CASE( test_switch )
{
  std::string testfile = bob::core::tmpfile("");
  std::string gztestfile = testfile + ".gz";
  std::string teststring = "** info test **";

  info.reset(testfile);
  info << teststring << std::endl;
  info.reset(gztestfile);

  //at this point checks if "testfile" is filled
  BOOST_CHECK(boost::filesystem::exists(testfile));
  BOOST_CHECK_EQUAL(get_contents(testfile), teststring + "\n");
  boost::filesystem::remove(testfile);

  info << teststring << std::endl;
  info.reset("null");
  
  //at this point checks if "testfile.gz" is filled
  BOOST_CHECK(boost::filesystem::exists(gztestfile));
  BOOST_CHECK_EQUAL(get_contents(gztestfile), teststring + "\n");
  boost::filesystem::remove(gztestfile);

  info << "NOT SUPPOSED TO BE PRINTED!" << std::endl;
}

//tests if I can read from files
BOOST_AUTO_TEST_CASE( test_input )
{
  std::string testfilename = bob::core::tmpfile("");
  bob::core::OutputStream ofile(testfilename);
  std::string testdata = "12345678,a_single_sentence";
  ofile << testdata << std::endl;
  ofile.close();
  bob::core::InputStream ifile(testfilename);
  std::string back;
  ifile >> back;
  BOOST_CHECK_EQUAL(testdata, back);
  //error << "File saved at: " << testfilename << std::endl;
  boost::filesystem::remove(testfilename);
}

//tests if I can read from compressed files
BOOST_AUTO_TEST_CASE( test_compressed_input )
{
  std::string testfilename = bob::core::tmpfile(".gz");
  bob::core::OutputStream ofile(testfilename);
  std::string testdata = "12345678,a_single_sentence";
  ofile << testdata << std::endl;
  ofile.close();
  bob::core::InputStream ifile(testfilename);
  std::string back;
  ifile >> back;
  BOOST_CHECK_EQUAL(testdata, back);
  //error << "File saved at: " << testfilename << std::endl;
  boost::filesystem::remove(testfilename);
}
