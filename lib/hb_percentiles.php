<?php
// Phoronix Test Suite module for hardware-bench: prints one JSON
// object per saved result file with each result's value and the
// OpenBenchmarking.org percentile data for its comparison hash. Queries
// OpenBenchmarking.org the same way the bundled ob_auto_compare module does
// (comparison hash + system type, never result values); falls back to the
// test profile's bundled generated.json. HB_OFFLINE=1 skips the query.
// Installed into the suite's user modules directory by hardware-bench.

class hb_percentiles extends pts_module_interface
{
	const module_name = 'hardware-bench percentiles';
	const module_version = '1.0.0';
	const module_description = 'Result values and OpenBenchmarking.org percentile data as JSON, for hardware-bench.';
	const module_author = 'hardware-bench';

	public static function user_commands()
	{
		return array('json' => 'to_json');
	}
	public static function to_json($r)
	{
		if(empty($r) || !pts_types::is_result_file($r[0]))
		{
			echo json_encode(array('error' => 'no result file')) . PHP_EOL;
			return false;
		}
		$offline = getenv('HB_OFFLINE') == '1' || !pts_network::internet_support_available();
		$system_type = phodevi_base::determine_system_type(phodevi::system_hardware(), phodevi::system_software());
		$result_file = new pts_result_file($r[0]);
		$out = array('system_type' => $system_type, 'retrieved' => time(), 'results' => array());
		foreach($result_file->get_result_objects() as $ro)
		{
			$tp = $ro->test_profile;
			$values = $ro->test_result_buffer->get_values();
			$hash = $ro->get_comparison_hash(true, false);
			$entry = array(
				'test' => $tp->get_identifier(false),
				'version' => $tp->get_test_profile_version(),
				'title' => $tp->get_title(),
				'arguments' => $ro->get_arguments_description(),
				'hardware_type' => $tp->get_test_hardware_type(),
				'unit' => $tp->get_result_scale(),
				'hib' => $tp->get_result_proportion() != 'LIB',
				'value' => is_numeric(end($values)) ? (float) end($values) : null,
				'comparison_hash' => $hash,
				'source' => null,
				'ae' => null,
			);
			if(!$offline)
			{
				$json = json_decode(pts_openbenchmarking::make_openbenchmarking_request('auto_compare_via_hash', array('comparison_hash' => $ro->get_comparison_hash(), 'system_type' => $system_type, 'test_profile' => $tp->get_identifier(false), 'comparison_hash_string' => $hash)), true);
				if(isset($json['openbenchmarking']['result']['ae']['percentiles']))
				{
					$entry['ae'] = $json['openbenchmarking']['result']['ae'];
					$entry['source'] = 'openbenchmarking.org';
				}
			}
			if($entry['ae'] === null && ($g = $tp->get_generated_data($hash)) && !empty($g['percentiles']))
			{
				$entry['ae'] = $g;
				$entry['source'] = 'bundled';
			}
			if(is_array($entry['ae']))
			{
				// Keep what hardware-bench uses; the full response also carries reference systems and timing data.
				$entry['ae'] = array_intersect_key($entry['ae'], array_flip(array('percentiles', 'samples', 'first_appeared', 'last_appeared', 'hib', 'unit', 'description')));
			}
			$out['results'][] = $entry;
		}
		echo json_encode($out) . PHP_EOL;
	}
}
